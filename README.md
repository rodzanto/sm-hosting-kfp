# ML hosting with Amazon SageMaker Components for Kubeflow Pipelines

For this workshop, we will use an Amazon EC2 instance as gateway for controlling our Kubeflow cluster in Amazon EKS. We will then work with a Jupyter notebook to setup some pipelines, exploring different machine learning inference options and model hosting features provided with Amazon SageMaker Components for Kubeflow Pipelines.

<img src="./images/f0.png" alt="pipeline" width="500"/>

**Objectives:**
1. Explore how to setup Kubeflow Pipelines with Amazon EC2 and Amazon EKS, and configuring roles for interacting with Amazon SageMaker
2. Explore how to configure and use [Amazon SageMaker Components for Kubeflow Pipelines](https://docs.aws.amazon.com/sagemaker/latest/dg/amazon-sagemaker-components-for-kubeflow-pipelines.html)
3. Get experience defining ML pipelines in Kubeflow that rely on Amazon SageMaker for processing, hyper-parameter optimization, training, batch inferences, and online deployment of hosting endpoints
4. Explore other hosting features provided in Amazon SageMaker like Elastic Inference, Endpoints with different model variants, or Model Monitoring

## Instructions

### Setup Kubeflow Pipelines and your AWS environment

*Note there are other resources for helping you creating the Kubeflow cluster from e.g. AWS Cloud9 like [this one](https://github.com/aws-samples/eks-kubeflow-cloudformation-quick-start). In this case we will use the EC2 approach directly.*

1. Access your AWS Console with the URL provided, make sure you are in the region of Oregon (us-west-2). Look for the service Amazon EC2 and go to Instances. Create an EC2 instance with image “Deep Learning AMI (Amazon Linux 2)” and instance type “t3.medium”. Create a SSH key and save it in a safe location (we will need it later).
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

6. Copy and paste your temporary credentials for being able to run the eksctl command in the next step. Note if you are using an AWS Event Engine workshop account you can copy this information directly from the dashboard, e.g.:
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
mkdir ${AWS_CLUSTER_NAME}
cd ${AWS_CLUSTER_NAME} && wget -O kfctl_aws.yaml $CONFIG_URI
```

- b. Go back to the AWS Console in your browser and go to Amazon SageMaker. Go to Notebook instances and “Create notebook instance”, put a Name, select “Notebook instance type” as “t3.medium”, expand the “Git repositories” menu and select “Clone a public Git repository” writing this URL: "https://github.com/rodzanto/sm-hosting-kfp/". Click “Create notebook instance”

- c. Configure Kubeflow: Again in your SSH terminal, make sure the cluster in step 7 is fully created before running this command:
```
aws eks update-kubeconfig --name 'kubeflow-sm' --region 'us-west-2'
export no_proxy=$no_proxy,.svc,.svc.cluster.local
export PATH=$PATH:/home/ec2-user
kfctl apply -V -f kfctl_aws.yaml
```
*Note 1: you might see a warning for cert-manager, let it re-try until the warning clears.*
*Note 2: in some rare cases kfctl might have issues for untar the file "vX.X-branch.tar.gz". In this case proceed to manually untar the file and point the "kfctl_aws.yaml" to this location (ask for AWS team help for this procedure if needed).*

- d. Verify the installation:
```
kubectl get nodes    ###check both nodes are Ready
kubectl -n kubeflow get all    ###wait for all showing Running
kubectl get ingress -n istio-system    ###provides the URL for accessing the KFP dashboard - access from your browser and setup the user 
```
*Note the last commands' output is the URL for the Kubeflow Pipelines Dashboard, and you can find the user and pass in the "kfctl_aws.yaml" file.*

- e. Setup AWS IAM permissions for the Service Account: First get the OIDC...
```
eksctl utils associate-iam-oidc-provider --cluster kubeflow-sm --region us-west-2 --approve
aws eks describe-cluster --name kubeflow-sm --query "cluster.identity.oidc.issuer" --output text    ###take note of the OIDC
```

- f. Now go back to the AWS console and look for the service IAM. Go to "Roles" and click the role that was created for the node-group (it should be called like: "eksctl-kubeflow-sm-nodegroup-cpu-NodeInstanceRole-XXXXXXXXX"). Click "Attach policies" and select the "AmazonSageMakerFullAccess" policy, click on "Attach policy", repeat for the policy "AmazonS3FullAccess". Finally, click on "Trust relationship" and "Edit trust relationship", replace the current policy with the following and hit "Update trust policy".

*Note: normally we would use here the OIDC that we got from the Kubeflow installation above to allow direct client interaction through the SDK with the annotated OIDC, but for the purposes of this workshop we will manually upload the pipeline packages to the Kubeflow Pipelines UI. For more details on the procedure you can check the [documentation here](https://docs.aws.amazon.com/sagemaker/latest/dg/usingamazon-sagemaker-components.html)*

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "ec2.amazonaws.com",
          "sagemaker.amazonaws.com"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Great, you now have a working Kubeflow cluster and everything setup on Amazon SageMaker and other services like Amazon S3. It is time to start defining the pipelines in the next steps.

### Lab #1: Creating your first pipeline with Amazon SageMaker Components for Kubeflow

1. In the AWS console look for Amazon SageMaker, click on "Notebook instances", and access your Jupyter notebook by clicking "Open Jupyter" (make sure the notebook is in status "InService").

2. MNIST Classification pipeline:
- Open the notebook "Components-pipelines", and follow the instructions to prepare the pipeline artifacts for this Lab.
- Now download the resulting file "mnist-classification-pipeline.tar.gz" to your PC, and open the Kubeflow Pipeline dashboard.
- Go to Pipelines in the left-menu, and click on "Upload pipeline", write Name and Description "mnist_classification" and select "File" pointing to the file you just downloaded, and hit "Create".
- Click on "Create experiment", with Name "mnist_classification" and hit "Next".
- Start your first run with "role_arn" the name of your node-group role from AWS IAM (should be something like: "arn:aws:iam::ACCOUNTID:role/eksctl-kubeflow-sm-nodegroup-cpu-NodeInstanceRole-XXXXXXXXXX"), and "bucket_name" the name of your S3 bucket (should be something like: "sagemaker-us-west-2-ACCOUNTID"), and hit "Start".
- Access your Run and monitor the execution of each step of the pipeline.

<img src="./images/f1.png" alt="pipeline" width="600"/>

- If you also want to run on-line predictions, you can use the "Predictions" notebook provided (Lab #1).

<img src="./images/f2.png" alt="pipeline" width="600"/>


### Lab #2: Exploring Amazon SageMaker Components with Elastic Inference and Endpoints with multiple model variants

1. Go back to the "Components-pipelines" notebook:
- Continue with the steps for the Lab #2
- Now download the resulting file "caltech-ei-mmv-pipeline.tar.gz" to your PC, and open the Kubeflow Pipeline dashboard.
- Go to Pipelines in the left-menu, and click on "Upload pipeline", write Name and Description "caltech_ei_mmv" and select "File" pointing to the file you just downloaded, and hit "Create".
- Click on "Create experiment", with Name "caltech_ei_mmv" and hit "Next".
- Start your first run with "role_arn" the name of your node-group role from AWS IAM (should be something like: "arn:aws:iam::ACCOUNTID:role/eksctl-kubeflow-sm-nodegroup-cpu-NodeInstanceRole-XXXXXXXXXX"), and "bucket_name" the name of your S3 bucket (should be something like: "sagemaker-us-west-2-ACCOUNTID"), and hit "Start".
- Access your Run and monitor the execution of each step of the pipeline.

<img src="./images/f3.png" alt="pipeline" width="600"/>

- If you also want to run on-line predictions, you can use the "Predictions" notebook provided (Lab #2). Note our model is not having a great accuracy as we shortened the training time for fitting the workshop duration, still, the proper categories are seen among the top of the list.

<img src="./images/f4.png" alt="pipeline" width="600"/>

### Lab #3: Exploring Amazon SageMaker Debugger and Model Monitor

1. Go back to the "Components-pipelines" notebook:
- Continue with the steps for the Lab #3
- Now download the resulting file "debugger-monitor-pipeline.tar.gz" to your PC, and open the Kubeflow Pipeline dashboard.
- Go to Pipelines in the left-menu, and click on "Upload pipeline", write Name and Description "debugger" and select "File" pointing to the file you just downloaded, and hit "Create".
- Click on "Create experiment", with Name "debugger" and hit "Next".
- Start your first run with "role_arn" the name of your node-group role from AWS IAM (should be something like: "arn:aws:iam::ACCOUNTID:role/eksctl-kubeflow-sm-nodegroup-cpu-NodeInstanceRole-XXXXXXXXXX"), and "bucket_name" the name of your S3 bucket (should be something like: "sagemaker-us-west-2-ACCOUNTID"), and hit "Start".
- Access your Run and monitor the execution of each step of the pipeline.

<img src="./images/f5.png" alt="pipeline" width="600"/>

- Now go back to the "Components-pipelines" notebook and continue with the steps there.
- After running the Model Monitor notebooks, if you want to run on-line predictions you can use the "Predictions" notebook provided (Lab #3).

Congratulations, you have reached the end of this workshop. For learning more, visit the documentation and GitHub examples.
