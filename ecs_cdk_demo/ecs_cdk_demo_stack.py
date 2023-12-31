from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_ecs,
    aws_ec2,
    aws_iam, 
    aws_ecr_assets, 
    aws_ecs_patterns, 
    aws_applicationautoscaling, 
    Size
)
from constructs import Construct

class EcsCdkDemoStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.vpc_id = "your_vpc_id"
        
        self.create_image_asset()
        self.create_ecs_cluster()
        self.create_ecs_task_definition()
        self.create_service()
        self.create_scheduled_task()
        
    
    def create_image_asset(self):
        self.image_asset = aws_ecr_assets.DockerImageAsset(
            scope=self,
            id="ecsCdkDemoImage",
            asset_name="ecsCdkDemoImage",
            directory="lib"
        )
        

    def create_ecs_cluster(self):

        self.vpc = aws_ec2.Vpc.from_lookup(
            scope=self, 
            id="ecsCdkDemoVPC", 
            vpc_id=self.vpc_id,
            region='ap-northeast-1'
        )
        
        self.cluster = aws_ecs.Cluster(
            scope=self,
            id="ecsCdkDemoCluster", 
            cluster_name="ecsCdkDemoCluster",
            vpc=self.vpc
        )
        self.cluster.apply_removal_policy(RemovalPolicy.DESTROY)
            
    
    def create_ecs_task_definition(self):
        # create task definition 
        self.task_definition = aws_ecs.FargateTaskDefinition(
            scope=self, 
            id="ecsCdkDemoTaskDeinition",
            family="ecsCdkDemoTaskDeinition",            
            memory_limit_mib =1024,
            cpu=512,
            runtime_platform=aws_ecs.RuntimePlatform(
                operating_system_family=aws_ecs.OperatingSystemFamily.LINUX,
                cpu_architecture=aws_ecs.CpuArchitecture.ARM64,
            )
        )
        self.task_definition.apply_removal_policy(RemovalPolicy.DESTROY)
        
        self.task_definition.add_to_execution_role_policy(aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW, 
            actions=[
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ], 
            resources=["*"]
        ))
    
        
        self.task_definition.add_to_task_role_policy(aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW, 
            actions=[
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "logs:CreateLogStream",
                "logs:PutLogEvents", 
                "s3:*",
                "s3-object-lambda:*", 
                "rds-data:ExecuteSql",
                "rds-data:ExecuteStatement",
                "rds-data:BatchExecuteStatement",
            ], 
            resources=["*"]
        ))

        self.task_definition.add_container(
            id="ecsTaskContainerImage",
            image=aws_ecs.ContainerImage.from_docker_image_asset(self.image_asset),
            logging=aws_ecs.LogDrivers.aws_logs(
                stream_prefix="sqsLambdaEcsDemo",
                mode=aws_ecs.AwsLogDriverMode.NON_BLOCKING,
                max_buffer_size=Size.mebibytes(25)
            )
        )
        
    def create_service(self):
        self.service = aws_ecs.FargateService(self, "Service",
            cluster=self.cluster,
            task_definition=self.task_definition,
            assign_public_ip=True,
            desired_count=1
        )
        self.service.apply_removal_policy(RemovalPolicy.DESTROY)

        

    def create_scheduled_task(self):
        self.scheduled_task = aws_ecs_patterns.ScheduledFargateTask(
            scope=self, 
            id="ecsCdkDemoScheduledTask", 
            scheduled_fargate_task_definition_options=aws_ecs_patterns.ScheduledFargateTaskDefinitionOptions(
                task_definition=self.task_definition
            ),
            cluster=self.cluster,
            schedule=aws_applicationautoscaling.Schedule.expression("cron(0 15 * * ? *)"),
            rule_name="ecsCdkDemoScheduledTask",
            desired_task_count=1, 
            vpc=self.vpc, 
            enabled=False # False: to turn the schedule task off, default to true
        )
        
     
