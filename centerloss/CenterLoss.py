# *_*coding:utf-8 *_*
import torch
import torch.nn as nn
from torch.autograd.function import Function

# torch.manual_seed(0)

class CenterLoss(nn.Module):
    def __init__(self, num_classes, feat_dim, size_average=True):
        super(CenterLoss, self).__init__()
        self.centers = nn.Parameter(torch.randn(num_classes, feat_dim))
        self.centerlossfunc = CenterLossFunc.apply
        self.feat_dim = feat_dim
        self.size_average = size_average
    def forward(self, label, feat):
        batch_size = feat.size(0) # 拿到批次
        feat = feat.view(batch_size, -1)
        if feat.size(1) != self.feat_dim:
            raise ValueError("Center's dim: {0} should be equal to input feature's "
                             "dim: {1}".format(self.feat_dim, feat.size(0)))
        batch_size_tensor = feat.new_empty(1).fill_(batch_size if self.size_average else 1)
        loss = self.centerlossfunc(feat, label, self.centers, batch_size_tensor)
        return loss

class CenterLossFunc(Function):
    @staticmethod
    def forward(ctx, feature, label, centers, batch_size):
        ctx.save_for_backward(feature, label, centers, batch_size)
        centers_batch = centers.index_select(0, label.long())
        return (feature - centers_batch).pow(2).sum() / 2.0 /batch_size
    @staticmethod
    def backward(ctx, grad_output):
        feature, label, centers, batch_size = ctx.saved_tensors
        centers_batch = centers.index_select(0, label.long()) # 选择标签对应的中心
        diff = centers_batch - feature
        # init every iteration
        counts = centers.new_ones(centers.size(0)) # 选择类别数量

        ones = centers.new_ones(label.size(0))
        grad_centers = centers.new_zeros(centers.size())

        counts = counts.scatter_add_(0, label.long(), ones)
        grad_centers.scatter_add_(0, label.unsqueeze(1).expand(feature.size()).long(), diff)
        grad_centers = grad_centers / counts.view(-1, 1)
        return - grad_output * diff / batch_size, None, grad_centers / batch_size, None


if __name__ == '__main__':
    torch.manual_seed(0)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ct = CenterLoss(10, 2, size_average=True).to(device)
    y = torch.Tensor([0,0,2,1]).to(device)
    feat = torch.zeros(4,2).to(device).requires_grad_()
    print(list(ct.parameters()))
    print(ct.centers.grad)
    out = ct(y, feat)
    print(out.item())
    out.backward() # 计算梯度
    print(ct.centers.grad)
    print(feat.grad)