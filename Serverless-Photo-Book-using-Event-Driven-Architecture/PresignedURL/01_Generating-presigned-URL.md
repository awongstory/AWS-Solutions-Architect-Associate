Lab tutorial here: https://amazon.qwiklabs.com/
NOTE : You'll need to search for "Building Serverless Applications with an Event-Driven Architecture on the catalog tab.

NOTE: Looking over the lab, I realized that there were a few things that were already "set-up". However, I ~~(refuse to pay!)~~ wanted to do things independently, so while I followed along their overall project breakdown, I took some liberties in my own implementation. You can pay for their labs (I find the monthly subscription more reasonable at $29 since it's unlimited credits for the month but don't want to commit for the year). 

In this project, I am building a web-based book printing app using a set of serverless technologies. My goals are to learn, and thus demonstrate:

1. Event-driven architecture
2. How Step Functions is configured to orchestrate serverless applications
3. How to take advantage of Amazon SQS and SNS
4. Create and configure Lambda functions and API Gateway resources
5. Made configuration updates to restore API functionality

The diagram of what I'm trying to accomplish looks like this:
 
![Workflow](PresignedURL/images/001-LambdaFlow.jpg)

## Key services used in this project:
1. Amazon API Gateway 
2. AWS Lambda - to run code, serverless. 
3. AWS EC2
4. AWS Step Functions - allows coordination of multiple AWS services into serverless workflows, allowing you to build and update apps quickly.
5. Amazon S3 - object storage service
6. Amazon Simple Queue Service/SQS
7. Amazon Simple Notification Service/SNS
8. Amazon Rekognition

## APIs used in this project:
1. **/presigned** - user sends request for presigned URLs to upload their images to an S3 bucket.
2. **/CreateBookBinding** - user triggers book creation process by indicating that they have finished uploading their images. This triggers the image-processing state machine.
3. **/execution** - the user approves the PDF by acknowledging an email from Amazon SNS

## Step Functions and state machines:
1. **ImageProcessStateMachine** : the job of this state machine is to pick up user-uploaded images from the S3 /Incoming folder, process the images, and create a PDF album for book printing. Key steps in this flow includes: image validation, resizing, watermarking. 
2. **BookprintStateMachine** : this state machine reads messages from the print vendor Amazon SQS and sends the photo book to a third-party vendor for printing. 

Let's get started!

### Generating pre-signed URLs: ###
[Sauce](https://catalog.us-east-1.prod.workshops.aws/v2/workshops/17f04680-db43-4fb6-85e9-c1f0b696c6c1/en-US/intro)
All objects on S3 buckets by default are private, with only the object owner having permission to access these objects. However, you can apply appropriate bucket/IAM policies to allow users to access these objects (for example, making objects public if you're using the S3 bucket to host a static website). Alternatively, you can also use presigned URLs where users can interact with objects without needing AWS credentials or IAM permissions. Presigned URLs are only valid for the specified duration. 

There are different ways to execute this, including using boto or serverless. However, I chose to implement this using a combination of EC2, S3, and IAM roles. 

1. Create key pair
- You need a key pair to access your EC2 instance. EC2 > Key Pairs > Create Key Pair
- Select pem if using SSH vs ppk if using Windows PuTTy. Download the pem/ppk for use later (you'll need the file path). For Windows 10 and newer, you can now use SSH in Powershell.

![Create key pair](PresignedURL/images/002-EC2KeyPair.jpg)

2. Create an EC2 instance
- On the left menu, go to Instances > Launch instances. 
- You'll choose an AMI or Amazon Machine Image. An Amazon Linux 2 AMI (Free tier) is absolutely fine here. You'll also choose your instance type, where the t2.micro is sufficient. 

![Create EC2 Instance](PresignedURL/images/006a-CreateEC2Instance.JPEG)

- Hit Next: Configure instance. Here, you leave just about everything default.

![Create EC2 Instance](PresignedURL/images/006b-CreateEC2Instance.jpg)

- Hit Next: Add storage. Leave everything default again.
- Hit Next: Add tags. Here, you can add a tag to identify your instance such as "name: EC2-photobook". 
- Hit Next: Configure Security Group. Leave everything default, and launch your instance.

![Configure Instance Security Group](PresignedURL/images/006c-CreateEC2securitygroup.jpg)

It should take a few seconds for your instance status to change to running. Then, take note your instance publicIP, it'll come in play later when we use SSH over Powershell.
 
![Copy paste EC2 PublicIP](PresignedURL/images/007-EC2config.JPEG)

3. Create S3 bucket

We also need to create our S3 bucket. I named mine `photobook-upload`. In configuring your bucket, turn OFF block all public access, and hit the checkmark where you acknowledge that this setting might result in the bucket becoming public. Hit Create bucket. 

![Create S3 bucket](PresignedURL/images/003-S3CreateBucket.jpg)

![Make bucket public](PresignedURL/images/004-MakeBucketPublic.jpg)

When your bucket is created, go to Permissions > Cross-origin resource sharing (CORS). CORS defines a way for client applications from one domain to interact with resources on another domain. The new console only accepts JSON now. The CORS configuration is 

```
[
    {
        "AllowedHeaders": [
            "Authorization"
        ],
        "AllowedMethods": [
            "PUT",
            "GET"
        ],
        "AllowedOrigins": [
            "*"
        ],
        "ExposeHeaders": [],
        "MaxAgeSeconds": 3000
    }
]
```

Save your changes. 

4. Create Lambda function.
The Lambda function will generate the presigned URL to upload the object. 
- Go to Amazon Lambda > Function > Create function.
- Select **Author from scratch**, and specify function name (e.g., PresignedUrlFunction).
- Select Node.js 12.x as the Runtime. 

![Create Lambda function](PresignedURL/images/008-CreateLambda.JPEG)

- Expand Choose or create an execution role > Create new role with basic Lambda permissions.
  This will create a role in IAM with basic lambda execution permissions (you'll edit this later). 
- Click Create Function. 

![Replace Lambda code](PresignedURL/images/011-LambdaCode.JPEG)

- Once function is created, go to Code, and replace function's code with:

```
var AWS = require('aws-sdk');
var s3 = new AWS.S3({
  signatureVersion: 'v4',
});


exports.handler = (event, context, callback) => {
  const url = s3.getSignedUrl('putObject', {
    Bucket: 'BUCKET NAME',
    Key: 'UploadedFile',
    Expires: 6000,
  });

  callback(null, url);
}
```

- Replace **`BUCKET NAME`** with your bucket name. 
- Go to Configuration > Permissions > Execution role > Role name. 

![Edit Lambda role](PresignedURL/images/012-LambdaRole.JPEG)

  - IAM role should open in new browser tab. Create an inline policy under Add permissions. 

![Add inline policy on IAM](PresignedURL/images/013-LambdaIAMinlinepolicy.JPEG)

  - You can do this either by using the visual editor or the JSON editor. Either way, replace the policy with the following, and replace **`BUCKET NAME`** with your S3 bucket name.

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3\:PutObject",
            "Resource": "arn\:aws\:s3:::BUCKET NAME/*"
        }
    ]
}
```
- Click Review, then Name your policy (eg., PresignedUrlBucketAccess_policy), and Create policy. 

5. Testing PUT access with Lambda
- Go back to Lambda browser, and Deploy function.
- Click Test, add your Event name (e.g, PresignedUrlTest) and leave everything else as default. Click Create.
- Click on Test once more, and expand Details.

![Test PUT access](PresignedURL/images/015-LambdaCodeTest.JPEG)

- Copy the generated URL (with the double quotes).

![Copy generated URL](PresignedURL/images/016-LambdaTestResult.JPEG)

- Copy the path of your .pem file and EC2 publicIP. On Windows 10 and newer, open Powershell and connect via SSH.

![SSH Powershell](PresignedURL/images/018-SSHPowershell.JPEG)

```
ssh -i C:\\pem PATH ec2-user@PUBLICIP
```

- Type yes to continue connecting, and your publicIP will be added to the list of known hosts. 
- Then type the following **with** double quotes around your presigned URL. 

```
curl -s PUT --data "This is my file content" --url "PRESIGNED URL RESULT"
```

- Check your S3 bucket; the new object is uploaded there. You can query it by selecting object > Actions > Query with S3 select > Run SQL Query.
- Your object should show your file content.

![Verify upload](PresignedURL/images/019-S3VerifyUpload.JPEG)

### And that's it on setting up presigned URLs on AWS! ###

In Part 2, we'll address configuring API Gateway as an endpoint. Thanks for reading thus far!
