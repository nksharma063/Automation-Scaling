import boto3
import time

# AWS credentials
aws_access_key_id = 'YOUR_ACCESS_KEY'
aws_secret_access_key = 'YOUR_SECRET_KEY'
region = 'Mumbai'

# S3 bucket configuration
s3_bucket_name = 'neeraj-storage'

# EC2 instance configuration
ec2_key_pair_name = 'neeraj-key-pair'
ec2_security_group_id = 'sg-neeraj'
ec2_instance_type = 't2.micro'
ec2_ami_id = 'YOUR_AMI_ID'  # Amazon Linux AMI, for example

# User data script for EC2 instance (install web server and deploy the app)
user_data_script = """#!/bin/bash
sudo yum update -y
sudo yum install -y httpd
sudo systemctl start httpd
sudo systemctl enable httpd
sudo yum install -y git
git clone https://github.com/nksharma063/travel-memory-app.git /var/www/html
"""

# Create S3 bucket
s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region)
s3.create_bucket(Bucket=s3_bucket_name)

# Launch EC2 instance
ec2 = boto3.resource('ec2', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region)
instance = ec2.create_instances(
    ImageId=ec2_ami_id,
    InstanceType=ec2_instance_type,
    KeyName=ec2_key_pair_name,
    SecurityGroupIds=[ec2_security_group_id],
    MinCount=1,
    MaxCount=1,
    UserData=user_data_script
)[0]

# Wait for the instance to be running
instance.wait_until_running()
instance.reload()

# Print instance information
print(f"EC2 Instance ID: {instance.id}")
print(f"Public IP Address: {instance.public_ip_address}")

# Add a delay to allow the instance to fully start before attempting to connect
time.sleep(60)

# ALB configuration
alb_name = 'neeraj-alb'
alb_security_group_id = 'sg-neeraj-alb'
alb_subnet_ids = ['subnet-id-1', 'subnet-id-2']  # Replace with your subnet IDs

# Target group configuration
target_group_name = 'neeraj-target-group'
target_group_port = 80

# Create ELB client
elbv2 = boto3.client('elbv2', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region)

# Create an Application Load Balancer (ALB)
alb_response = elbv2.create_load_balancer(
    Name=alb_name,
    Subnets=alb_subnet_ids,
    SecurityGroups=[alb_security_group_id],
    Scheme='internet-facing',
    Tags=[
        {
            'Key': 'Name',
            'Value': alb_name
        },
    ]
)

# Get the DNS name of the ALB
alb_dns_name = alb_response['LoadBalancers'][0]['DNSName']
print(f"ALB DNS Name: {alb_dns_name}")

# Create a target group
target_group_response = elbv2.create_target_group(
    Name=target_group_name,
    Protocol='HTTP',
    Port=target_group_port,
    VpcId='neeraj-vnet',  # Replace with your VPC ID
    HealthCheckProtocol='HTTP',
    HealthCheckPort='80',
    HealthCheckPath='/',
    HealthCheckIntervalSeconds=30,
    HealthCheckTimeoutSeconds=5,
    HealthyThresholdCount=2,
    UnhealthyThresholdCount=2,
    Tags=[
        {
            'Key': 'Name',
            'Value': target_group_name
        },
    ]
)

# Get the target group ARN
target_group_arn = target_group_response['TargetGroups'][0]['TargetGroupArn']
print(f"Target Group ARN: {target_group_arn}")

# Register the EC2 instance with the target group
elbv2.register_targets(
    TargetGroupArn=target_group_arn,
    Targets=[
        {
            'Id': instance.id,
            'Port': target_group_port,
        },
    ]
)

print(f"EC2 instance {instance.id} registered with the target group.")

# Add a delay to allow the ALB to be fully provisioned
time.sleep(60)


# Auto Scaling Group configuration
asg_name = 'neeraj-asg'
min_size = 2
max_size = 5
desired_capacity = 2
cooldown = 300  # cooldown period in seconds

# Launch Configuration configuration
lc_name = 'neeraj-lc'
instance_type = 't2.micro'
key_name = 'neeraj-key-pair'
security_groups = ['sg-neeraj']

# Scaling policies configuration
scale_out_policy_name = 'neeraj-scale-out-policy'
scale_in_policy_name = 'neeraj-scale-in-policy'

# CloudWatch metric configuration
scale_out_threshold = 80
scale_in_threshold = 20

# Create ASG client
autoscaling = boto3.client('autoscaling', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region)

# Create Launch Configuration
lc_response = autoscaling.create_launch_configuration(
    LaunchConfigurationName=lc_name,
    ImageId=ec2_ami_id,  # Amazon Linux AMI, for example
    InstanceType=instance_type,
    KeyName=key_name,
    SecurityGroups=security_groups,
)

# Create Auto Scaling Group
asg_response = autoscaling.create_auto_scaling_group(
    AutoScalingGroupName=neeraj-ASG,
    LaunchConfigurationName=lc_name,
    MinSize=min_size,
    MaxSize=max_size,
    DesiredCapacity=desired_capacity,
    Cooldown=cooldown,
    VPCZoneIdentifier='subnet-id-1,subnet-id-2',  # Replace with your subnet IDs
    Tags=[
        {
            'Key': 'Name',
            'Value': asg_name,
            'PropagateAtLaunch': True
        },
    ]
)

# Create scale-out policy
scale_out_policy = autoscaling.put_scaling_policy(
    AutoScalingGroupName=neeraj-asg,
    PolicyName=scale_out_policy_name,
    PolicyType='TargetTrackingScaling',
    TargetTrackingConfiguration={
        'PredefinedMetricSpecification': {
            'PredefinedMetricType': 'ASGAverageCPUUtilization',
        },
        'TargetValue': scale_out_threshold,
    }
)

# Create scale-in policy
scale_in_policy = autoscaling.put_scaling_policy(
    AutoScalingGroupName=neeraj-asg,
    PolicyName=scale_in_policy_name,
    PolicyType='TargetTrackingScaling',
    TargetTrackingConfiguration={
        'PredefinedMetricSpecification': {
            'PredefinedMetricType': 'ASGAverageCPUUtilization',
        },
        'TargetValue': scale_in_threshold,
    }
)

# Add a delay to allow the ASG to be fully provisioned
time.sleep(60)

print(f"Auto Scaling Group {asg_name} created with scaling policies.")



