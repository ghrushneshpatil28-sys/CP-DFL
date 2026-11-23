"""The only image classifier factory used by this project."""
import torch.nn as nn
from torchvision.models import resnet18, ResNet18_Weights
from torchvision.models.resnet import BasicBlock


class DPBasicBlock(BasicBlock):
    """Identical ResNet18 residual computation without an inplace addition."""
    def forward(self, x):
        identity = self.downsample(x) if self.downsample is not None else x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        return self.relu(out + identity)


def build_resnet18(num_classes: int, pretrained: bool = False):
    if num_classes < 2:
        raise ValueError("At least two verified classes are required")
    weights = ResNet18_Weights.DEFAULT if pretrained else None
    model = resnet18(weights=weights)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


def use_group_norm(model):
    """DP-compatible ResNet18 variant; normalization is recorded in metadata."""
    for name, child in model.named_children():
        if isinstance(child, BasicBlock):
            child.__class__ = DPBasicBlock
        if isinstance(child, nn.BatchNorm2d):
            replacement = nn.GroupNorm(min(32, child.num_features), child.num_features, eps=child.eps)
            replacement.weight.data.copy_(child.weight.data)
            replacement.bias.data.copy_(child.bias.data)
            setattr(model, name, replacement)
        else:
            use_group_norm(child)
    for module in model.modules():
        if isinstance(module, nn.ReLU):
            module.inplace = False
    return model
