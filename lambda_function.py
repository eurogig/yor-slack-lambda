import json
import logging as logger
import os
import urllib3
import boto3

# Set up http request maker thing
http = urllib3.PoolManager()

# Read all the environment variables
SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']
SLACK_USER = os.environ['SLACK_USER']
SLACK_CHANNEL = os.environ['SLACK_CHANNEL']
TESTMODE = 'false'

def lambda_handler(event,context):
    
    gitHubURL='https://localhost'
    commitURL='https://localhost'
    awsURL='https://localhost'
    
    # TESTMODE is only if we're adding a new resource.  The Cloudwatch events are a bit
    # randon at times for different resources so this mode will spill the entire event
    # into slack for debug of extreme verbosity mode
    if TESTMODE=='true':
        message = json.dumps(event)
        slack_message = {
        'channel': SLACK_CHANNEL,
        'username': SLACK_USER,
        'text':message
        }

    else:
        resourceType=event["detail"]["requestParameters"]["evaluations"][0]["complianceResourceType"]
        awsRegion=event["region"]
        awsAccount=event["account"]
        resInstance=event["detail"]["requestParameters"]["evaluations"][0]["complianceResourceId"]
        [aws,service,restype] =resourceType.lower().split("::")
        if resourceType=="AWS::EC2::Instance":
            resourceARN="arn:{0}:{1}:{2}:{3}:{4}/{5}".format(aws,service,awsRegion,awsAccount,restype,resInstance)
        elif resourceType=="AWS::S3::Bucket":
            resourceARN="arn:{0}:{1}:::{2}".format(aws,service,resInstance)


        failedRule=event["detail"]["additionalEventData"]["managedRuleIdentifier"]
        try:
            failureDesc=event["detail"]["requestParameters"]["evaluations"][0]["annotation"] 
        except KeyError as e:
            failureDesc="AWS Resource Failed check: {0}".format(failedRule)
            
        # Construct a new slack message
    
        restag = boto3.client('resourcegroupstaggingapi')
        try:
            response = restag.get_resources(ResourceARNList=[resourceARN] )
        except restag.exceptions.InvalidParameterException as e:
            return("Unrecognised resource type" + resourceARN)

    
#        s3=boto3.resource('s3')
#        resourceTags = s3.BucketTagging(bucketname)
        resourceTags=response["ResourceTagMappingList"][0]["Tags"]     
        for tags in resourceTags:
            if tags['Key']=="git_modifiers":
                git_modifiers=tags["Value"]
            if tags['Key']=="git_last_modified_by":
                git_last_modified_by=tags["Value"]
            if tags['Key']=="git_file":
                git_file=tags["Value"]
            if tags['Key']=="git_repo":
                git_repo=tags["Value"]
            if tags['Key']=="git_last_modified_at":
                git_last_modified_at=tags["Value"]
            if tags['Key']=="git_org":
                git_org=tags["Value"]
            if tags['Key']=="git_commit":
                git_commit=tags["Value"]
            if tags['Key']=="yor_trace":
                yor_trace=tags["Value"]
    
        # Construct a new slack message
        message = '{6} \nResource id: {7}\nLast modifier: *<@{0}>*\nLast modified: {4} \n \
    You can trace the resource from cloud to code:  See the resource\n  \n'.format(git_last_modified_by,git_file,git_org,git_repo,git_last_modified_at,yor_trace,failureDesc,resInstance)
        gitHubURL='https://github.com/{0}/{1}/search?q={2}'.format(git_org,git_repo,yor_trace)
        commitURL='https://github.com/{0}/{1}/search?q={2}'.format(git_org,git_repo,git_commit)
        awsURL='https://{0}.console.aws.amazon.com/config/home?region={0}#/resources?resourceId={1}'.format(awsRegion,resInstance)
        slack_message = {
            'channel': SLACK_CHANNEL,
            'username': SLACK_USER,
                'blocks': [
        		{
        			"type": "section",
        			"text": {
        				"type": "mrkdwn",
        				"text": message
        			}
        		},
    		    {
        			"type": "divider"
        		},
        		{
        			"type": "actions",
        			"elements": [
        				{
        					"type": "button",
        					"text": {
        						"type": "plain_text",
        						"text": "Trace on GitHub"
    
        					},
        					"value": "click_me_123",
        					"url": gitHubURL
        				},
        				{
        					"type": "button",
        					"text": {
        						"type": "plain_text",
        						"text": "See Commit on GitHub"
        					},
        					"value": "click_me_123",
        					"url": commitURL
        				},
        				{
        					"type": "button",
        					"text": {
        						"type": "plain_text",
        						"text": "See Resource on AWS"
        					},
        					"value": "click_me_123",
        					"url": awsURL
        				}    				
        			]
        		}
        	]
        }

    encoded_data=json.dumps(slack_message)
    # Post message on SLACK_WEBHOOK_URL
    try:
        resp = http.request(
            "POST",
            SLACK_WEBHOOK_URL, 
            body=encoded_data, # Embedding JSON data into request body.
            headers={"Content-Type": "application/json"}
        )
    
    except urllib3.exceptions.HTTPError as e:
        print('Request failed:', e.reason)
    
    return (resp.status)

