from config import config
import os
def main():
    srcfloder = config.train_path
    outFile = open(config.train_path.split('/')[-1],'w')
    childFolders = os.listdir(srcfloder)
    num = 0
    for childfloder in childFolders:
        secondfile = srcfloder + '/' + childfloder
        allFiles = os.listdir(secondfile)
        for fileline in allFiles:
            print(num)
            imgfile = secondfile + '/' + fileline +'\t'+str(num)+'\n'
            outFile.write(imgfile)
            outFile.flush()
        num += 1
    outFile.close()
if __name__ == "__main__":
    main()