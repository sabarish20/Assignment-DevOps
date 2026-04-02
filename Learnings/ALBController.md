# Deploying Nginx Ingress Controller with ALB on EKS

## Architecture Overview

When exposing the Nginx Ingress Controller using a Kubernetes `Service` of type `LoadBalancer`, AWS defaults to provisioning an **NLB (Layer 4)** or Classic Load Balancer. To use an **Application Load Balancer (ALB / Layer 7)** in front of Nginx, you must use the **AWS Load Balancer Controller**.

The traffic flow is:

```
Internet → AWS ALB → Nginx Ingress Controller (NodePort) → Application Pods
```

---

## Required Permissions

Your base EKS cluster needs:

| Role | Policy |
|---|---|
| Cluster Role | `AmazonEKSClusterPolicy` |
| Worker Role | `AmazonEKSWorkerNodePolicy` |
| Worker Role | `AmazonEKS_CNI_Policy` |
| Worker Role | `AmazonEC2ContainerRegistryReadOnly` |

For the **AWS Load Balancer Controller**, you additionally need:

- An **OIDC Provider** attached to the EKS cluster (enables IRSA — IAM Roles for Service Accounts)
- A dedicated **IAM Role** bound to the `aws-load-balancer-controller` Kubernetes Service Account
- The **AWS Load Balancer Controller IAM Policy** attached to that role (downloaded from the official repo)

---

## Step 1: Terraform — Add OIDC & ALB Controller IAM Role

Add to `Terraform/modules/EKS/alb-role.tf`:

```hcl
data "tls_certificate" "eks" {
  url = aws_eks_cluster.k8s.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.k8s.identity[0].oidc[0].issuer
}

data "http" "aws_load_balancer_controller_policy" {
  url = "https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.1/docs/install/iam_policy.json"
}

resource "aws_iam_policy" "aws_load_balancer_controller" {
  name   = "${var.eks_name}-AWSLoadBalancerControllerIAMPolicy"
  policy = data.http.aws_load_balancer_controller_policy.response_body
}

data "aws_iam_policy_document" "aws_load_balancer_controller_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:sub"
      values   = ["system:serviceaccount:kube-system:aws-load-balancer-controller"]
    }

    principals {
      identifiers = [aws_iam_openid_connect_provider.eks.arn]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "aws_load_balancer_controller" {
  assume_role_policy = data.aws_iam_policy_document.aws_load_balancer_controller_assume_role_policy.json
  name               = "${var.eks_name}-AmazonEKSLoadBalancerControllerRole"
}

resource "aws_iam_role_policy_attachment" "aws_load_balancer_controller_attach" {
  role       = aws_iam_role.aws_load_balancer_controller.name
  policy_arn = aws_iam_policy.aws_load_balancer_controller.arn
}

output "aws_load_balancer_controller_role_arn" {
  value = aws_iam_role.aws_load_balancer_controller.arn
}
```

> **Note:** Using the `http` data source avoids needing to commit the policy JSON file. If you instead use `file("${path.module}/alb_iam_policy.json")`, that file must exist in the repository or Terraform will throw:
> `Invalid function argument: no file exists at "modules/EKS/alb_iam_policy.json"`

---

## Step 2: Install the AWS Load Balancer Controller (Helm)

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=<YOUR_EKS_CLUSTER_NAME> \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=<ARN_FROM_TERRAFORM_OUTPUT>
```

---

## Step 3: Install Nginx Ingress Controller as NodePort (Helm)

Set the service type to `NodePort` so Nginx does **not** create its own AWS Load Balancer:

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=NodePort \
  --set controller.service.targetPorts.http=http \
  --set controller.service.targetPorts.https=https
```

---

## Step 4: Create the ALB Ingress (routes ALB → Nginx)

### Option A: YAML (ClusterResources/ALB-Ingress.yaml)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: alb-to-nginx
  namespace: ingress-nginx
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: instance
    alb.ingress.kubernetes.io/healthcheck-path: /healthz
spec:
  ingressClassName: alb
  rules:
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: ingress-nginx-controller
                port:
                  number: 80
```

```bash
kubectl apply -f ClusterResources/ALB-Ingress.yaml
```

### Option B: Terraform (kubernetes_ingress_v1)

```hcl
resource "kubernetes_ingress_v1" "alb_to_nginx" {
  metadata {
    name      = "alb-to-nginx"
    namespace = "ingress-nginx"
    annotations = {
      "alb.ingress.kubernetes.io/scheme"           = "internet-facing"
      "alb.ingress.kubernetes.io/target-type"      = "instance"
      "alb.ingress.kubernetes.io/healthcheck-path" = "/healthz"
    }
  }

  spec {
    ingress_class_name = "alb"
    rule {
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = "ingress-nginx-controller"
              port {
                number = 80
              }
            }
          }
        }
      }
    }
  }

  depends_on = [helm_release.aws_load_balancer_controller]
}
```

> **Important:** Always add `depends_on = [helm_release.aws_load_balancer_controller]` so Terraform waits for the controller to be running before creating the Ingress. If the Ingress is created before the controller is ready, Kubernetes accepts the resource but no ALB is provisioned.

---

## Key Concepts

| Concept | Explanation |
|---|---|
| **IRSA** | IAM Roles for Service Accounts — links a Kubernetes Service Account to an AWS IAM Role via the OIDC provider |
| **OIDC Provider** | Allows AWS to trust Kubernetes-issued tokens, enabling pods to assume IAM roles without static credentials |
| **NodePort** | Nginx is exposed on a port on each EC2 worker node so the ALB can route traffic to it |
| **ingressClassName: alb** | Tells the AWS Load Balancer Controller to manage this Ingress and provision an ALB |
| **target-type: instance** | ALB routes to EC2 node IPs + NodePort (as opposed to `ip` which routes directly to pod IPs via VPC CNI) |
| **Listener Rules** | You do **not** manage these manually. The AWS Load Balancer Controller reads the `rules` block in the Kubernetes Ingress and automatically creates the corresponding ALB Listener Rules in AWS |
