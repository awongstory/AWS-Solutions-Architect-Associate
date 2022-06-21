import os
import json
import uuid
import boto3

from PIL import Image

# bucketname for pixelated images
processed_bucket=os.environ['processed_bucket']

s3_client = boto3.client('s3')

def lambda_handler(event, context):
	print(event)

	# get bucket and object key from event object
	source_bucket = event['Records'][0]['s3']['bucket']['name']
	key = event['Records'][0]['s3']['object']['key']

	# Generate a temp name, and set location for our original image
	object_key = str(uuid.uuid4()) + '-' + key
	img_download_path = '/tmp/{}'.format(object_key)

	# Download the source image from S3 to temp location within execution environment
	with open(img_download_path, 'wb') as img_file:
		s3_client.download_fileobj(source_bucket, key, img_file)

	# Biggify the pixels and store temp pixelated versions
	resize(img_download_path, '/tmp/resized-1754-{}'.format(object_key))

	# uploading the pixelated version to destination bucket
	upload_key = '/tmp/resized-1754-{}'.format(object_key)
	s3_client.upload_file('/tmp/resized-1754-{}'.format(object_key), processed_bucket, 'resized-1754-{}.jpg'.format(key))

def resize(image_path, resized_img_path):
	img = Image.open(image_path)
	basewidth = 1754
	width, height = img.size
	if height > width:
		img = img.rotate(90, expand=True)
	wpercent = (basewidth / float(width))
	hsize = int((float(height) * float(wpercent)))
	pixelsize = basewidth, hsize
	img.thumbnail(pixelsize)
	img.save(resized_img_path)
