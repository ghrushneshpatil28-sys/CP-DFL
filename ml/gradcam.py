"""Grad-CAM for canonical ResNet18 layer4, with bounded hook lifetimes."""
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image


def gradcam(model, tensor, image, class_index=None):
    activations = []
    handle = model.layer4.register_forward_hook(lambda module, args, output: activations.append(output))
    try:
        model.zero_grad(set_to_none=True)
        with torch.enable_grad():
            logits = model(tensor.requires_grad_(True))
            index = int(logits.argmax(1).item()) if class_index is None else class_index
            gradients = torch.autograd.grad(logits[0, index], activations[0])[0]
            weights = gradients.mean(dim=(2, 3), keepdim=True)
            cam = F.relu((weights * activations[0]).sum(1, keepdim=True))
            cam = F.interpolate(cam, size=(image.height, image.width), mode="bilinear", align_corners=False)[0, 0]
            cam = cam.detach().cpu().numpy()
            cam = (cam - cam.min()) / max(float(cam.max() - cam.min()), 1e-8)
        heat = np.stack([cam, .3 * (1 - np.abs(2 * cam - 1)), 1 - cam], axis=-1)
        overlay = np.clip(.6 * np.asarray(image.convert("RGB")) + .4 * 255 * heat, 0, 255).astype(np.uint8)
        return Image.fromarray(overlay), torch.softmax(logits.detach(), dim=1)[0].cpu().tolist()
    finally:
        handle.remove()
        model.zero_grad(set_to_none=True)
