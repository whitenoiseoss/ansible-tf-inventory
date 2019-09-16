import json
import boto3

# read file (tfstate)
# in the beginning, lets just have the file locally and read it
# eventually this will need to read from S3

# s3 = boto3.client('s3')
# with open('FILE_NAME', 'wb') as f:
#    s3.download_fileobj('BUCKET_NAME', 'OBJECT_NAME', f)

asgc = boto3.client('autoscaling')
ec2 = boto3.client('ec2')
asg_names = list()


with open('terraform.tfstate', 'r') as f:
    tfstate = json.load(f)

for r in tfstate['resources']:
    if r['type'] == "aws_autoscaling_group":
        asg_names.append(r['instances'][0]['attributes']['id'])

resp = asgc.describe_auto_scaling_groups(AutoScalingGroupNames=asg_names)

# now we have our autoscaling group names, so we can describe them
# from there we get tags and instances


class InventoryFactory:
    def __init__(self, data):
        # ansible groups, directly correlated with asg tags
        self.groups = dict()
        self.data = data

    def _create_group_list(self):
        for asg in self.data['AutoScalingGroups']:
            temp_groups = list()
            temp_inst_data = list()

            # populate our groups
            for t in asg['Tags']:
                group_name = "%s_%s" % (t['Key'], t['Value'])
                group_name = group_name.replace('-', '').lower()
                if group_name not in self.groups:
                    self.groups[group_name] = list()
                temp_groups.append(group_name)

            for i in asg['Instances']:
                temp_inst_data.append(i['InstanceId'])

            instance_data = ec2.describe_instances(
                InstanceIds=temp_inst_data,
                DryRun=False,
            )
            instances = instance_data['Reservations'][0]['Instances']
            temp_inst_data = list()

            for i in instances:
                for temp_group in temp_groups:
                    self.groups[temp_group].append(i['PrivateIpAddress'])

    def create_inventory(self):
        self._create_group_list()
        output = ""

        for group, ips in self.groups.items():
            output += "[%s]\n%s\n\n" % (group, "\n".join(ips))

        print(output)


IF = InventoryFactory(resp)
IF.create_inventory()
