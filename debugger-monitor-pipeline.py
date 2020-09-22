#!/usr/bin/env python3

import kfp
import json
import os
import copy
from kfp import components
from kfp import dsl

sagemaker_train_op = components.load_component_from_url('https://github.com/kubeflow/pipelines/raw/master/components/aws/sagemaker/train/component.yaml')
sagemaker_model_op = components.load_component_from_url('https://github.com/kubeflow/pipelines/raw/master/components/aws/sagemaker/model/component.yaml')
sagemaker_deploy_op = components.load_component_from_url('https://github.com/kubeflow/pipelines/raw/master/components/aws/sagemaker/deploy/component.yaml')

def training_input(input_name, s3_uri, content_type):
    return {
        "ChannelName": input_name,
        "DataSource": {"S3DataSource": {"S3Uri": s3_uri, "S3DataType": "S3Prefix"}},
        "ContentType": content_type
    }

def training_debug_hook(s3_uri, collection_dict):
    return {
        'S3OutputPath': s3_uri,
        'CollectionConfigurations': format_collection_config(collection_dict)
    }

def format_collection_config(collection_dict):
    output = []
    for key, val in collection_dict.items():
        output.append({'CollectionName': key, 'CollectionParameters': val})
    return output

def training_debug_rules(rule_name, parameters):
    return {
        'RuleConfigurationName': rule_name,
        'RuleEvaluatorImage': '915447279597.dkr.ecr.us-west-2.amazonaws.com/sagemaker-debugger-rules:latest',
        'RuleParameters': parameters
    }

collections = {
    'feature_importance' : {
        'save_interval': '5'
    },
    'losses' : {
        'save_interval': '10'
    },
    'average_shap': {
        'save_interval': '5'
    },
    'metrics': {
        'save_interval': '3'
    }
}

bad_hyperparameters = {
    'max_depth': '5',
    'eta': '0',
    'gamma': '4',
    'min_child_weight': '6',
    'silent': '0',
    'subsample': '0.7',
    'num_round': '50'
}

@dsl.pipeline(
    name='XGBoost Training Pipeline with bad hyperparameters',
    description='SageMaker training job test with debugger'
)
def training(role_arn="", bucket_name="my-bucket"):
    region = "us-west-2"
    train_channels = [
        training_input("train", f"s3://{bucket_name}/mnist_kmeans_example/input/valid-data.csv", 'text/csv')
    ]
    train_debug_rules = [
        training_debug_rules("LossNotDecreasing", {"rule_to_invoke": "LossNotDecreasing", "tensor_regex": ".*"}),
        training_debug_rules("Overtraining", {'rule_to_invoke': 'Overtraining', 'patience_train': '10', 'patience_validation': '20'}),
    ]
    training = sagemaker_train_op(
        region=region,
        image='246618743249.dkr.ecr.us-west-2.amazonaws.com/sagemaker-xgboost:0.90-2-cpu-py3',
        hyperparameters=bad_hyperparameters,
        channels=train_channels,
        instance_type='ml.m5.2xlarge',
        model_artifact_path=f's3://{bucket_name}/mnist_kmeans_example/output/model',
        debug_hook_config=training_debug_hook(f's3://{bucket_name}/mnist_kmeans_example/hook_config', collections),
        debug_rule_config=train_debug_rules,
        role=role_arn,
    )
    create_model = sagemaker_model_op(
        region=region,
        model_name=training.outputs["job_name"],
        image=training.outputs["training_image"],
        model_artifact_url=training.outputs["model_artifact_url"],
        role=role_arn,
    )

    sagemaker_deploy_op(
        region=region, model_name_1=create_model.output,
    )

if __name__ == '__main__':
    kfp.compiler.Compiler().compile(training, __file__ + '.zip')
