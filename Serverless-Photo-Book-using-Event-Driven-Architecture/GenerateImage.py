# only if you're running this on your computer
# this is not the Lambda function

from PIL import Image
import glob

# specify folder path or execute in specified folder
imagelist = glob.glob('*.jpg')

def openimage(image_list):
    # gotta get list first
    # then open image, resize image, convert from byte to jpg format
    # save file under original file name to different filepath/bucket name
    # append to list
    # have to refine my image-resizing, or rotate image so it fits dimensions
    new_list = []
    for i in image_list:
        image = Image.open(i)
        width, height = image.size
        # if image is portrait, rotate it:
        if height > width:
            image = image.rotate(90, expand=True)
        image.thumbnail((1754, 1240))
        image_filename = i.split(".")[0]
        image.save(image_filename + '.jpg', format='JPEG')
        new_list.append(image_filename + '.jpg')
    return(new_list)

def split_list(new_list):
    # zip one list into pairs to create pairs of images
    # odd image will create pair with black image
    split_list = list(zip(new_list[::2], new_list[1::2]))
    return(split_list)

def convert_to_PDF(split_list, pdfname):
    # convert pairs of jpg files into multiple PDF pages
    # append pages to each other to make 1 file
    # write and save to file
    merged_imagelist = []
    for x, y in split_list:
        image1 = Image.open(x)
        image2 = Image.open(y)
        merged_image = Image.new('RGB', (image1.width, image1.height + image2.height))
        merged_image.paste(image1, (0,0))
        merged_image.paste(image2, (0, image1.height))
        merged_image = merged_image.convert('RGB')
        merged_imagelist.append(merged_image)
    merged_image.save(pdfname, save_all=True, append_images=merged_imagelist[:-1])

new_list = openimage(imagelist)
updated_list = split_list(new_list)
convert_to_PDF(updated_list, 'FILENAME.pdf')

