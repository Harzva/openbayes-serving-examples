# -*- coding: utf-8 -*-

# -- stdlib --
from io import BytesIO

# -- third party --
from PIL import Image
from torchvision import models, transforms
import requests
import torch

import openbayes_serving as serv

# -- own --


# -- code --
class PythonPredictor:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"using device: {self.device}")

        model = models.detection.fasterrcnn_resnet50_fpn(pretrained=False, pretrained_backbone=False)
        model.load_state_dict(torch.load("fasterrcnn_resnet50_fpn_coco-258fb6c6.pth"))
        model = model.to(self.device)
        model.eval()

        self.preprocess = transforms.Compose([transforms.ToTensor()])

        with open("coco_labels.txt") as f:
            self.coco_labels = f.read().splitlines()

        self.model = model

    def predict(self, json):
        threshold = float(json["threshold"])
        image = requests.get(json["url"]).content
        img_pil = Image.open(BytesIO(image))
        img_tensor = self.preprocess(img_pil).to(self.device)
        img_tensor.unsqueeze_(0)

        with torch.no_grad():
            pred = self.model(img_tensor)

        predicted_class = [self.coco_labels[i] for i in pred[0]["labels"].cpu().tolist()]
        predicted_boxes = [
            [(i[0], i[1]), (i[2], i[3])] for i in pred[0]["boxes"].detach().cpu().tolist()
        ]
        predicted_score = pred[0]["scores"].detach().cpu().tolist()
        predicted_t = [predicted_score.index(x) for x in predicted_score if x > threshold]
        if len(predicted_t) == 0:
            return [], []

        predicted_t = predicted_t[-1]
        predicted_boxes = predicted_boxes[: predicted_t + 1]
        predicted_class = predicted_class[: predicted_t + 1]
        return predicted_boxes, predicted_class


if __name__ == '__main__':
    serv.run(PythonPredictor)
