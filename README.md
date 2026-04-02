# DevOps Assignment 

As part of this assignment, I have successfully implemented an end-to-end CI/CD pipeline that provisions infrastructure (Amazon EKS) and deploys the application to the EKS cluster in accordance with the specified requirements.

Additionally, I have integrated security checks to identify vulnerabilities and misconfigurations in the Docker image, Terraform configurations, and Helm charts. Further details regarding the design decisions can be discussed during the review call.

I have also implemented separate CI/CD pipelines for both Infrastructure as Code (IaC) and application deployments to ensure better modularity and maintainability.

An Application Load Balancer was implemented as a separate deployment. However, for the one-click deployment setup, I provisioned a lightweight NGINX Ingress Controller to create a load balancer, optimizing for simplicity and faster execution.

Currently, the pipeline build is marked as UNSTABLE, which has been intentionally configured. This is due to the presence of identified security misconfigurations; however, it does not block any stages of the pipeline or the application deployment process.

Please refer to the screenshots available in the Screenshots folder for additional details.

The following tasks outlined in the assignment have been successfully completed:
- Executed Terraform commands to provision infrastructure
- Built the Docker image for the sample application
- Pushed the Docker image to a container registry (ECR preferred)
- Deployed the application to the EKS cluster using Helm

Thank you for the oppurtunity !