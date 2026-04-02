pipeline {
    agent none

    parameters {
        choice(
            name: 'ACTION',
            choices: ['apply', 'destroy'],
            description: 'Terraform action — "destroy" automatically skips the Application phase'
        )
        booleanParam(
            name: 'SKIP_INFRA',
            defaultValue: false,
            description: 'Skip all Terraform / IaC stages (use when infrastructure is already provisioned)'
        )
        booleanParam(
            name: 'SKIP_APP',
            defaultValue: false,
            description: 'Skip all Application CI/CD stages'
        )
    }

    environment {
        AWS_ACCESS_KEY_ID     = credentials('AWS_ACCESS_KEY_ID')
        AWS_SECRET_ACCESS_KEY = credentials('AWS_SECRET_ACCESS_KEY')
        AWS_DEFAULT_REGION    = 'ap-south-1'
        AWS_REGION            = 'ap-south-1'

        ECR_REGISTRY    = credentials('ECR_REGISTRY')
        BACKEND_IMAGE   = 'ecolibirium-backend'
        FRONTEND_IMAGE  = 'ecolibirium-frontend'
        IMAGE_TAG       = "${env.BUILD_NUMBER}"
        EKS_CLUSTER     = credentials('EKS_CLUSTER_NAME')
        HELM_RELEASE    = 'assignment-eco'
        HELM_CHART_PATH = './Helm'
        HELM_NAMESPACE  = 'ecolibirium'
        GITHUB_EMAIL    = credentials('GITHUB_EMAIL')
        GITHUB_USERNAME = credentials('GITHUB_USERNAME')
    }

    stages {
        stage('IaC — Scan & Plan') {
            when {
                beforeAgent true
                expression { !params.SKIP_INFRA }
            }
            agent {
                docker {
                    image 'hashicorp/terraform:1.14.7'
                    args  '--entrypoint= -u root'
                }
            }
            stages {

                stage('IaC — Checkov Scan') {
                    when {
                        expression { params.ACTION != 'destroy' }
                    }
                    steps {
                        catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                            sh '''
                                apk add --no-cache python3 py3-pip
                                pip3 install checkov --quiet --break-system-packages

                                checkov -d Terraform \
                                        --hard-fail-on CRITICAL \
                                        --output cli \
                                        --quiet
                            '''
                        }
                    }
                }

                stage('IaC — Terraform Init') {
                    steps {
                        dir('Terraform') {
                            sh 'terraform init'
                        }
                    }
                }

                stage('IaC — Terraform FMT') {
                    steps {
                        dir('Terraform') {
                            catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                                sh 'terraform fmt -check'
                            }
                        }
                    }
                }

                stage('IaC — Terraform Validate') {
                    steps {
                        dir('Terraform') {
                            sh 'terraform validate'
                        }
                    }
                }

                stage('IaC — Terraform Plan') {
                    steps {
                        dir('Terraform') {
                            script {
                                if (params.ACTION == 'destroy') {
                                    sh 'terraform plan -destroy'
                                } else {
                                    sh 'terraform plan -out=tfplan'
                                }
                            }
                        }
                    }
                }

            }
        }

        stage('IaC — Review and Approval') {
            when {
                beforeAgent true
                expression { !params.SKIP_INFRA }
            }
            agent none
            steps {
                input message: "Approve Terraform ${params.ACTION}?",
                      ok: "Proceed with ${params.ACTION}"
            }
        }

        stage('IaC — Terraform Action') {
            when {
                beforeAgent true
                expression { !params.SKIP_INFRA }
            }
            agent {
                docker {
                    image 'hashicorp/terraform:1.14.7'
                    args  '--entrypoint= -u root'
                }
            }
            steps {
                dir('Terraform') {
                    script {
                        if (params.ACTION == 'destroy') {
                            sh 'terraform destroy -auto-approve'
                        } else {
                            sh 'terraform apply -auto-approve'
                        }
                    }
                }
            }
        }

             stage('IaC — Nginx Ingress Provisioning') {
            when {
                beforeAgent true
                allOf {
                    expression { !params.SKIP_INFRA }
                    expression { params.ACTION == 'apply' }
                }
            }
            agent {
                docker {
                    image 'ubuntu:22.04'
                    args  '-u root'
                }
            }
            steps {
                sh '''
                    export DEBIAN_FRONTEND=noninteractive
                    apt-get update -y -q
                    apt-get install -y -q curl unzip
 
                    # AWS CLI
                    curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
                    unzip -q awscliv2.zip && ./aws/install --update
 
                    # kubectl
                    curl -sLO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
                    chmod +x kubectl && mv kubectl /usr/local/bin/kubectl
 
                    # Helm
                    curl -s https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
 
                    # Connect to cluster
                    aws eks update-kubeconfig --region ${AWS_DEFAULT_REGION} --name ${EKS_CLUSTER}
 
                    # ── Install Nginx Ingress Controller ──────────────────────
                    # EKS automatically creates a Classic Load Balancer for the
                    # controller service (type: LoadBalancer). No ALB Controller,
                    # no IAM role annotation, no NodePort wiring required.
                    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
                    helm repo update
 
                    helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
                        --namespace ingress-nginx \
                        --create-namespace \
                        --wait \
                        --timeout 3m
 
                    # FIX: Wait until the controller is truly ready before
                    # returning — pods Running is not enough.
                    kubectl wait deployment ingress-nginx-controller \
                        -n ingress-nginx \
                        --for=condition=available \
                        --timeout=120s
 
                    echo "============================================"
                    echo "Nginx Ingress Load Balancer hostname:"
                    kubectl get svc ingress-nginx-controller -n ingress-nginx \
                        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
                    echo ""
                    echo "============================================"
                '''
            }
        }

        stage('App — CI/CD') {
            when {
                beforeAgent true
                allOf {
                    expression { !params.SKIP_APP }
                    expression { params.ACTION != 'destroy' }
                }
            }
            agent {
                docker {
                    image 'ubuntu:22.04'
                    args  '-v /var/run/docker.sock:/var/run/docker.sock -u root'
                }
            }
            stages {

                stage('App — Setup Tools') {
                    steps {
                        sh '''
                            export DEBIAN_FRONTEND=noninteractive

                            apt-get update -y
                            apt-get install -y curl unzip docker.io wget apt-transport-https gnupg git python3-pip

                            wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | apt-key add -
                            echo "deb https://aquasecurity.github.io/trivy-repo/deb generic main" > /etc/apt/sources.list.d/trivy.list
                            apt-get update -y
                            apt-get install -y trivy

                            curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
                            unzip -q -o awscliv2.zip
                            ./aws/install --update

                            curl -LO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
                            chmod +x kubectl && mv kubectl /usr/local/bin/kubectl

                            curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

                            wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
                            chmod +x /usr/local/bin/yq

                            python3 -m pip install checkov
                        '''
                    }
                }

                stage('App — Build') {
                    parallel {
                        stage('Backend') {
                            steps {
                                script {
                                    env.BACKEND_IMG_ID = docker.build(
                                        "${ECR_REGISTRY}/${BACKEND_IMAGE}:${IMAGE_TAG}",
                                        "./Application/FlaskApp/Backend"
                                    ).id
                                }
                            }
                        }
                        stage('Frontend') {
                            steps {
                                script {
                                    env.FRONTEND_IMG_ID = docker.build(
                                        "${ECR_REGISTRY}/${FRONTEND_IMAGE}:${IMAGE_TAG}",
                                        "./Application/FlaskApp/Frontend"
                                    ).id
                                }
                            }
                        }
                    }
                }

                stage('App — Trivy Scan') {
                    parallel {
                        stage('Scan Backend') {
                            steps {
                                sh '''
                                    trivy image --exit-code 1 \
                                                --severity CRITICAL \
                                                --no-progress \
                                                --scanners vuln \
                                                ${ECR_REGISTRY}/${BACKEND_IMAGE}:${IMAGE_TAG}
                                '''
                            }
                        }
                        stage('Scan Frontend') {
                            steps {
                                sh '''
                                    trivy image --exit-code 1 \
                                                --severity CRITICAL \
                                                --no-progress \
                                                --scanners vuln \
                                                ${ECR_REGISTRY}/${FRONTEND_IMAGE}:${IMAGE_TAG}
                                '''
                            }
                        }
                    }
                }

                stage('App — Push to ECR') {
                    parallel {
                        stage('Push Backend') {
                            steps {
                                script {
                                    docker.withRegistry("https://${ECR_REGISTRY}", "ecr:${AWS_REGION}:aws-credentials") {
                                        def img = docker.image("${ECR_REGISTRY}/${BACKEND_IMAGE}:${IMAGE_TAG}")
                                        img.push()
                                        img.push('latest')
                                    }
                                }
                            }
                        }
                        stage('Push Frontend') {
                            steps {
                                script {
                                    docker.withRegistry("https://${ECR_REGISTRY}", "ecr:${AWS_REGION}:aws-credentials") {
                                        def img = docker.image("${ECR_REGISTRY}/${FRONTEND_IMAGE}:${IMAGE_TAG}")
                                        img.push()
                                        img.push('latest')
                                    }
                                }
                            }
                        }
                    }
                }

                stage('App — Helm Checks') {
                    parallel {
                        stage('Checkov Helm Scan') {
                            steps {
                                catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                                    sh '''
                                        echo "--- Running Checkov on Helm Chart ---"
                                        checkov -d ${HELM_CHART_PATH} \
                                            --framework helm \
                                            --output cli \
                                            --compact \
                                            --soft-fail-on LOW,MEDIUM,HIGH
                                    '''
                                }
                            }
                        }
                    }
                }

                stage('App — Update Helm Image Tags') {
                    steps {
                        withCredentials([usernamePassword(
                            credentialsId: 'github-pat',
                            usernameVariable: 'GIT_USER',
                            passwordVariable: 'GIT_TOKEN'
                        )]) {
                            sh '''
                                git config --global --add safe.directory "${WORKSPACE}"

                                yq e '.backend.image.tag  = "'${IMAGE_TAG}'"' -i ${HELM_CHART_PATH}/values.yaml
                                yq e '.frontend.image.tag = "'${IMAGE_TAG}'"' -i ${HELM_CHART_PATH}/values.yaml

                                git config user.email "${GITHUB_EMAIL}"
                                git config user.name  "${GITHUB_USERNAME}"

                                git add ${HELM_CHART_PATH}/values.yaml
                                git commit -m "ci: update image tags to build ${IMAGE_TAG} [skip ci]"

                                REPO_URL=$(git remote get-url origin | sed 's|https://||')
                                git push https://${GIT_USER}:${GIT_TOKEN}@${REPO_URL} HEAD:main
                            '''
                        }
                    }
                }

                stage('App — Deploy to EKS') {
                    steps {
                        withCredentials([[
                            $class: 'AmazonWebServicesCredentialsBinding',
                            credentialsId: 'aws-credentials'
                        ]]) {
                            sh '''
                                aws eks update-kubeconfig --region ${AWS_REGION} --name ${EKS_CLUSTER}

                                kubectl get namespace ${HELM_NAMESPACE} || kubectl create namespace ${HELM_NAMESPACE}

                                if ! helm upgrade --install ${HELM_RELEASE} ${HELM_CHART_PATH} \
                                        --namespace ${HELM_NAMESPACE} \
                                        --set backend.image.tag=${IMAGE_TAG} \
                                        --set frontend.image.tag=${IMAGE_TAG} \
                                        --wait \
                                        --timeout 5m; then
                                    echo "Helm deploy failed — rolling back to previous revision..."
                                    helm rollback ${HELM_RELEASE} 0 --namespace ${HELM_NAMESPACE} || true
                                    exit 1
                                fi

                                kubectl rollout status deployment/assignment-eco-backend-deployment  -n ${HELM_NAMESPACE} --timeout=3m
                                kubectl rollout status deployment/assignment-eco-frontend-deployment -n ${HELM_NAMESPACE} --timeout=3m

                                docker rmi ${ECR_REGISTRY}/${BACKEND_IMAGE}:${IMAGE_TAG}  || true
                                docker rmi ${ECR_REGISTRY}/${FRONTEND_IMAGE}:${IMAGE_TAG} || true

                                chown -R 1000:1000 ${WORKSPACE}
                            '''
                        }
                    }
                }

            }
        }

    }

    post {
        success {
            script {
                if (!params.SKIP_INFRA && !params.SKIP_APP && params.ACTION == 'apply') {
                    echo "Full deployment complete — Terraform infra provisioned and build ${IMAGE_TAG} deployed to EKS."
                } else if (!params.SKIP_INFRA && params.ACTION == 'destroy') {
                    echo "Terraform destroy complete — infrastructure torn down."
                } else if (!params.SKIP_INFRA) {
                    echo "Terraform ${params.ACTION} complete."
                } else {
                    echo "Build ${IMAGE_TAG} deployed to EKS successfully."
                }
            }
        }
        unstable {
            echo 'Pipeline completed with warnings — review Checkov / Terraform FMT results.'
        }
        failure {
            echo 'Pipeline failed — check stage logs above.'
        }
    }
}
