# Models Hosting with Amazon SageMaker Components for Kubeflow Pipelines

For this workshop, we will create an Amazon EC2 instance that will act as the gateway node for controlling our Kubeflow cluster, and will later work with a Jupyter notebook to prepare a Kubeflow Pipeline. Finally, we will run some examples for going through the options that Amazon SageMaker provides for model inferences through the use of Components for Kubeflow Pipelines.


## Instructions

1. Access your AWS Console with the URL provided, make sure you are in the region of Oregon (us-west-2). Look for the service Amazon EC2 and go to Instances. Create an EC2 instance with image “DeepLearning AMI (Linux)” and instance type “t3.medium”. Create a SSH key and save it in a safe location (we will need it later).
*Note we are using the DeepLearning AMI as it already comes with some packages that we would need later.*

2. Open a terminal in your PC and make sure you do "chmod 400 xxxx.pem" to your downloaded key from the previous step.

3. Wait for the instance to be ready in the EC2 Instances' console. SSH to the instance from the terminal in your PC with user "ec2-user", and the public IP of your instance (you can check this IP by going to "Connect" in the EC2 Instances' console), e.g.:
```
ssh -i "xxxxxx.pem" ec2-user@ec2-X-X-X-X.us-west-2.compute.amazonaws.com
```

4. Install kubectl from your terminal:
```
curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
kubectl version --client
```

5. Now, install eksctl:
```
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
curl -o aws-iam-authenticator https://amazon-eks.s3.us-west-2.amazonaws.com/1.17.9/2020-08-04/bin/linux/amd64/aws-iam-authenticator
chmod +x ./aws-iam-authenticator
mkdir -p $HOME/bin && cp ./aws-iam-authenticator $HOME/bin/aws-iam-authenticator && export PATH=$PATH:$HOME/bin
echo 'export PATH=$PATH:$HOME/bin' >> ~/.bashrc
aws-iam-authenticator help
```

6. Copy and paste your credentials for being able to run AWS CLI commands, e.g.:
```
export AWS_DEFAULT_REGION=us-west-2
export AWS_ACCESS_KEY_ID=xxxxxxxxxxxxxx
export AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxx
export AWS_SESSION_TOKEN=xxxxxxxxxxxxxx
```

7. Still from the SSH terminal, create an Amazon EKS cluster. We will use this cluster for running Kubeflow Pipelines:
```
eksctl create cluster \
--name kubeflow-sm \
--version 1.17 \
--region us-west-2 \
--nodegroup-name cpu-nodes \
--node-type c5.xlarge \
--nodes 2 \
--node-volume-size 50 \
--timeout=40m \
--auto-kubeconfig
```
*Note this step should take around 15 mins or so (do not close the SSH session in the meantime!). Once complete it should show "EKS cluster in region is ready".

8. Still from the SSH terminal, configure Kubeflow:

- a. Prepare the environment:
```
wget https://github.com/kubeflow/kfctl/releases/download/v1.1.0/kfctl_v1.1.0-0-g9a3621e_linux.tar.gz
tar -xvf kfctl_v1.1.0-0-g9a3621e_linux.tar.gz
export PATH=$PATH:/home/ec2-user
export CONFIG_URI="https://raw.githubusercontent.com/kubeflow/manifests/v1.1-branch/kfdef/kfctl_aws.v1.1.0.yaml"
export AWS_CLUSTER_NAME=kubeflow-sm
mkdir ${AWS_CLUSTER_NAME} && cd ${AWS_CLUSTER_NAME}
wget -O kfctl_aws.yaml $CONFIG_URI
```

- b. Go back to the AWS Console in your browser and go to Amazon SageMaker. Go to Notebook instances and “Create notebook instance”, put a Name, select “Notebook instance type” as “t3.medium”, expand the “Git repositories” menu and select “Clone a public Git repository” writing this URL: <>. Click “Create notebook instance”

- c. Configure Kubeflow: Again in your SSH terminal, make sure the cluster in step 7 is fully created before running this command:
```
aws eks update-kubeconfig --name 'kubeflow-sm' --region 'us-west-2'
export no_proxy=$no_proxy,.svc,.svc.cluster.local
export PATH=$PATH:/home/ec2-user
kfctl apply -V -f kfctl_aws.yaml
```
*Note you might see a warning for cert-manager, let it re-try until the warning clears.*

- d. Verify the installation:
```
kubectl get nodes    (check both ready)
kubectl -n kubeflow get all    (wait for Running)
kubectl get ingress -n istio-system    (provides the URL for accessing the KFP dashboard) 
```

- f. Setup AWS IAM permissions for the Service Account:
```
eksctl utils associate-iam-oidc-provider --cluster kubeflow-sm --region us-west-2 --approve
aws eks describe-cluster --name kubeflow-sm --query "cluster.identity.oidc.issuer" --output text    (take note of the OIDC)
```
Go back to the AWS console and look for the service IAM. Go to "Roles" and click the role created for the node-group





