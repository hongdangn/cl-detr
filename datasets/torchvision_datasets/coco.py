"""
Copy-Paste from torchvision, but add utility of caching images on memory
"""
from torchvision.datasets.vision import VisionDataset
from PIL import Image
import os
import os.path
import tqdm
from io import BytesIO
# from datasets.pycocotools import COCO
from pycocotools.coco import COCO

class CocoDetection(VisionDataset):

    def __init__(self, root, annFile, args, cls_order, phase_idx, incremental, incremental_val, val_each_phase, balanced_ft, tfs_or_tfh, num_of_phases, cls_per_phase, seed_data, transform=None, target_transform=None, transforms=None,cache_mode=False, local_rank=0, local_size=1):
        super(CocoDetection, self).__init__(root, transforms, transform, target_transform)
        self.coco = COCO(annFile)

        if "train" in annFile:
            self.cats = list(range(0, 150)) if phase_idx == 0 else list(range(150, 221))
            self.ids = []

            for c_idx in self.cats:
                img_ids = self.coco.getImgIds(catIds=c_idx)
                self.ids.extend(img_ids)
            
            self.ids = list(set(self.ids))
            print("CURRENT TRAIN CAT_IDS: {}\nLEN_IDS: {}".format(self.cats, len(self.ids)))
        else:
            self.ids = self.coco.getImgIds()
            print("CURRENT VAL CAT_IDS: {}\nLEN_IDS {}".format(sorted(self.coco.getCatIds()), len(self.ids)))

        self.cache_mode = cache_mode
        self.local_rank = local_rank
        self.local_size = local_size
        if cache_mode:
            self.cache = {}
            self.cache_images()

    def cache_images(self):
        self.cache = {}
        for index, img_id in zip(tqdm.trange(len(self.ids)), self.ids):
            if index % self.local_size != self.local_rank:
                continue
            path = self.coco.loadImgs(img_id)[0]['file_name']
            with open(os.path.join(self.root, path), 'rb') as f:
                self.cache[path] = f.read()

    def get_image(self, path):
        if self.cache_mode:
            if path not in self.cache.keys():
                with open(os.path.join(self.root, path), 'rb') as f:
                    self.cache[path] = f.read()
            return Image.open(BytesIO(self.cache[path])).convert('RGB')
        return Image.open(os.path.join(self.root, path)).convert('RGB')

    def __getitem__(self, index):
        """
        Args:
            index (int): Index
        Returns:
            tuple: Tuple (image, target). target is the object returned by ``coco.loadAnns``.
        """
        coco = self.coco
        img_id = self.ids[index]
        ann_ids = coco.getAnnIds(imgIds=img_id)
        target = coco.loadAnns(ann_ids)

        path = coco.loadImgs(img_id)[0]['file_name']

        img = self.get_image(path)
        if self.transforms is not None:
            img, target = self.transforms(img, target)

        return img, target

    def __len__(self):
        return len(self.ids)
