#!/usr/bin/env python3


import kfp
from kfp import components
from kfp import dsl

sagemaker_train_op = components.load_component_from_url('https://github.com/kubeflow/pipelines/raw/master/components/aws/sagemaker/train/component.yaml')
sagemaker_model_op = components.load_component_from_url('https://github.com/kubeflow/pipelines/raw/master/components/aws/sagemaker/model/component.yaml')
sagemaker_deploy_op = components.load_component_from_url('https://github.com/kubeflow/pipelines/raw/master/components/aws/sagemaker/deploy/component.yaml')

def training_input(input_name, s3_uri):
    return {
        "ChannelName": input_name,
        "DataSource": {"S3DataSource": {"S3Uri": s3_uri, "S3DataType": "S3Prefix", "S3DataDistributionType": "FullyReplicated"}},
        "ContentType": 'application/x-recordio'
    }

@dsl.pipeline(
    name="CALTECH-EI-MMV-pipeline",
    description="CALTECH Elastic Inference and Multi-Model Variant image classification pipeline in SageMaker",
)
def caltech_classification(role_arn="", bucket_name=""):
    # Common component inputs
    region = "us-west-2"
    instance_type = "ml.p3.2xlarge"
    train_image = "433757028032.dkr.ecr.us-west-2.amazonaws.com/image-classification:latest"

    # Training input and output location based on bucket name
    train_channels = [
        training_input("train", f"s3://{bucket_name}/caltech_example/train"),
        training_input("validation", f"s3://{bucket_name}/caltech_example/validation")
    ]
    train_output_location = f"s3://{bucket_name}/caltech_example/output"

    training1 = sagemaker_train_op(
        region=region,
        image=train_image,
        volume_size = 50,
        max_run_time = 360000,
        training_input_mode= 'File',
        hyperparameters={
              "num_layers": "18", 
              "image_shape": "3,224,224",
              "num_classes": "257",
              "num_training_samples": "15420",
              "mini_batch_size": "256",
              "epochs": "10",
              "learning_rate": "0.1",
              "top_k": "2"
        },
        channels=train_channels,
        instance_type=instance_type,
        model_artifact_path=train_output_location,
        role=role_arn,
    )

    create_model1 = sagemaker_model_op(
        region=region,
        model_name=training1.outputs["job_name"],
        image=training1.outputs["training_image"],
        model_artifact_url=training1.outputs["model_artifact_url"],
        role=role_arn,
    )

    training2 = sagemaker_train_op(
        region=region,
        image=train_image,
        volume_size = 50,
        max_run_time = 360000,
        training_input_mode= 'File',
        hyperparameters={
              "num_layers": "18", 
              "image_shape": "3,224,224",
              "num_classes": "257",
              "num_training_samples": "15420",
              "mini_batch_size": "256",
              "epochs": "15",
              "learning_rate": "0.05",
              "top_k": "2"
        },
        channels=train_channels,
        instance_type=instance_type,
        model_artifact_path=train_output_location,
        role=role_arn,
    )

    create_model2 = sagemaker_model_op(
        region=region,
        model_name=training2.outputs["job_name"],
        image=training2.outputs["training_image"],
        model_artifact_url=training2.outputs["model_artifact_url"],
        role=role_arn,
    )

    deploy1 = sagemaker_deploy_op(
        region=region,
        model_name_1=create_model1.output,
        model_name_2=create_model2.output,
        accelerator_type_1='ml.eia1.medium',
        accelerator_type_2='ml.eia1.medium'
    )
    
    deploy2 = sagemaker_deploy_op(
        region=region,
        model_name_1=create_model1.output
    )

if __name__ == "__main__":
    kfp.compiler.Compiler().compile(caltech_classification, __file__ + ".zip")