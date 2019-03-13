from PIL import Image
from torchvision import transforms as T
class Train_DATA(object):
    def __init__(self,root):
        imgs = []
        file = open(root,'r')
        for i in file.readlines():
            temp = i.replace('\n','').split('\t')
            imgs.append(temp)
        self.imgs = imgs
        self.transforms = T.Compose([
            T.RandomHorizontalFlip(),
            T.ToTensor(),
            T.Normalize([0.5,0.5,0.5],[0.5,0.5,0.5])])
    def __getitem__(self, index):
        img_path = self.imgs[index][0]
        label = int(self.imgs[index][1])
        data = Image.open(img_path)
        data = self.transforms(data)
        return data,label
    def __len__(self):
        return len(self.imgs)