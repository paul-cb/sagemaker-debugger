import boto3


class SageMakerUtils:
    @staticmethod
    def is_sagemaker_job_finished(jobname, returnMock=None):
        if returnMock is not None:
            return returnMock
        client = boto3.client('sagemaker')
        response = client.describe_training_job(TrainingJobName=jobname)
        status = response['TrainingJobStatus']
        if status in ['InProgress', 'Stopping']:
            return False
        elif status in ['Completed', 'Failed', 'Stopped']:
            return True  # return 1 if the job is finished

    @staticmethod
    def terminate_sagemaker_job(jobname):
        client = boto3.client('sagemaker')
        try :
            client.stop_training_job(TrainingJobName=jobname)
        except Exception as e:
            print(e)

    @staticmethod
    def add_tags(sm_job_name, tags):
        client = boto3.client('sagemaker')
        # TODO create resource arn here
        resource_arn = 'arn:aws:sagemaker:us-east-1:072677473360:training-job/' + sm_job_name
        try:
            client.add_tags(ResourceArn=resource_arn, Tags=tags)
        except Exception as e:
            print(e)