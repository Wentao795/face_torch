from torch.nn import Linear,Conv2d,BatchNorm1d,BatchNorm2d,PReLU,ReLU,Sigmoid,Dropout2d,Dropout,AvgPool2d,MaxPool2d,AdaptiveAvgPool2d,Sequential,Module,Parameter
import torch.nn.functional as F
import torch
import math
import pdb
from  collections import namedtuple
class Flatten(Module):
    def forward(self,input):
        return input.view(input.size(0),-1)

def l2_norm(input,axis=1):
    #axis grap row  so axis = 0 replace cel,kuahang.
    norm = torch.norm(input,2,axis,True)#(x,l2 norm,kualieqiu,baozhiweidububian)
    output = torch.div(input,norm)#a / |a|
    return output


##input attetion??
class SEModule(Module):
    def __init__(self,channels,reduction):
        super(SEModule,self).__init__()
        self.avg_pool = AdaptiveAvgPool2d(1)
        self.fc1 = Conv2d(channels,channels // reduction,kernel_size=1,padding=0,bias=False)
        self.relu = ReLU(inplace=True)
        self.fc2 = Conv2d(channels // reduction,channels,kernel_size=1,padding=0,bias=False)
        self.sigmoid = Sigmoid()

    def forward(self, x):
        module_input = x
        x = self.avg_pool(x)
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        x = self.sigmoid(x)
        return module_input * x

class bottleneck_IR(Module):
    def __init__(self,in_channel,depth,stride):
        super(bottleneck_IR,self).__init__()
        if in_channel == depth:
            self.shorcut_layer = MaxPool2d(1,stride)
        else:
            self.shorcut_layer = Sequential(
                Conv2d(in_channel,depth,(1,1),stride,bias=False),
                BatchNorm2d(depth)
            )
        self.res_layer = Sequential(
            BatchNorm2d(in_channel),
            Conv2d(in_channel,depth,(3,3),(1,1),1,bias=False),
            PReLU(depth),
            Conv2d(depth,depth,(3,3),stride,1,bias=False),
            BatchNorm2d(depth)
        )

    def forward(self, x):
        shortcut = self.shorcut_layer(x)
        res = self.res_layer(x)
        return res + shortcut

class bottleneck_IR_SE(Module):
    def __init__(self,in_channel,depth,stride):
        super(bottleneck_IR_SE,self).__init__()
        if in_channel == depth:
            self.shortcut_layer = MaxPool2d(1,stride)
        else:
            self.shortcut_layer = Sequential(
                Conv2d(in_channel,depth,(1,1),stride,bias=False),
                BatchNorm2d(depth)
            )
        self.res_layer = Sequential(
            BatchNorm2d(in_channel),
            Conv2d(in_channel,depth,(3,3),(1,1),1,bias=False),
            PReLU(depth),
            Conv2d(depth,depth,(3,3),stride,1,bias=False),
            BatchNorm2d(depth),
            SEModule(depth,16)
        )

    def forward(self, x):
        shortcut = self.shortcut_layer(x)
        res = self.res_layer(x)
        return res + shortcut

class Bottleneck(namedtuple('Block',['in_channel','depth','stride'])):
    """"""

def get_block(in_channel,depth,num_units,stride = 2):
    return [Bottleneck(in_channel,depth,stride)] + [Bottleneck(depth,depth,1) for i in range(num_units - 1)]

def get_blocks(num_layers):
    if num_layers == 50:
        blocks = [
            get_block(in_channel=64,depth=64,num_units=3),
            get_block(in_channel=64, depth=128, num_units=4),
            get_block(in_channel=128, depth=256, num_units=14),
            get_block(in_channel=256, depth=512, num_units=3),
        ]
    elif num_layers == 100:
        blocks = [
            get_block(in_channel=64, depth=64, num_units=3),
            get_block(in_channel=64, depth=128, num_units=13),
            get_block(in_channel=128, depth=256, num_units=30),
            get_block(in_channel=256, depth=512, num_units=3),
        ]
    elif num_layers == 152:
        blocks = [
            get_block(in_channel=64, depth=64, num_units=3),
            get_block(in_channel=64, depth=128, num_units=8),
            get_block(in_channel=128, depth=256, num_units=36),
            get_block(in_channel=256, depth=512, num_units=3),
        ]
    return blocks

class Backbone(Module):
    def __init__(self,num_layers,drop_ration,mode='ir'):
        super(Backbone,self).__init__()
        assert num_layers in [50,100,152]
        assert mode in ['ir','ir_se']
        blocks = get_blocks(num_layers)
        if mode == 'ir':
            unit_module = bottleneck_IR
        elif mode == 'ir_se':
            unit_module = bottleneck_IR_SE
        self.input_layer = Sequential(
            Conv2d(3,64,(3,3),1,1,bias=False),
            BatchNorm2d(64),
            PReLU(64)
        )
        self.output_layer = Sequential(
            BatchNorm2d(512),
            Dropout(drop_ration),
            Flatten(),
            Linear(512*7*7,512),
            BatchNorm1d(512)
        )

        modules = []
        for block in blocks:
            for bottleneck in block:
                modules.append(unit_module(bottleneck.in_channel,
                                           bottleneck.depth,
                                           bottleneck.stride))
        self.body = Sequential(*modules)

    def forward(self, x):
        x = self.input_layer(x)
        x = self.body(x)
        x = self.output_layer(x)
        return l2_norm(x)

class Conv_block(Module):
    def __init__(self,in_c,out_c,kernel=(1,1),stride=(1,1),padding=(1,1),groups=1):
        super(Conv_block,self).__init__()
        self.conv = Conv2d(in_c,out_channels=out_c,kernel_size=kernel,groups=groups,stride=stride,padding=padding,bias=False)
        self.bn = BatchNorm2d(out_c)
        self.prelu = PReLU(out_c)

    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        x = self.prelu(x)
        return x

class Linear_block(Module):
    def __init__(self,in_c,out_c,kernel=(1,1),stride=(1,1),padding=(0,0),groups=1):
        super(Linear_block,self).__init__()
        self.conv = Conv2d(in_c,out_channels=out_c,kernel_size=kernel,groups=groups,stride=stride,padding=padding,bias=False)
        self.bn = BatchNorm2d(out_c)
    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        return x
class Depth_Wise(Module):
    def __init__(self,in_c,out_c,residual=False,kernel=(3,3),stride=(2,2),padding=(1,1),groups=1):
        super(Depth_Wise,self).__init__()
        self.conv = Conv_block(in_c,out_c=groups,kernel=(1,1),padding=(0,0),stride=(1,1))
        self.conv_dw = Conv_block(groups,groups,groups=groups,kernel=kernel,padding=padding,stride=stride)
        self.project = Linear_block(groups,out_c,kernel=(1,1),padding=(0,0),stride=(1,1))
        self.residual = residual
    def forward(self, x):
        if self.residual:
            short_cut = x
        x = self.conv(x)
        x = self.conv_dw(x)
        x = self.project(x)
        if self.residual:
            output = short_cut + x
        else:
            output = x
        return output

class Residual(Module):
    def __init__(self,c,num_block,groups,kernel=(3,3),stride=(1,1),padding=(1,1)):
        super(Residual,self).__init__()
        modules = []
        for _ in range(num_block):
            modules.append(Depth_Wise(c,c,residual=True,kernel=kernel,padding=padding,stride=stride,groups=groups))
        self.model = Sequential(*modules)
    def forward(self, x):
        return self.model(x)

class MobileFaceNet(Module):
    def __init__(self,embedding_size):
        super(MobileFaceNet,self).__init__()
        self.conv1 = Conv_block(3,64,kernel=(3,3),stride=(2,2),padding=(1,1))
        self.conv2_dw = Conv_block(64,64,kernel=(3,3),stride=(1,1),padding=(1,1),groups=64)
        self.conv_23 = Depth_Wise(64,64,kernel=(3,3),stride=(2,2),padding=(1,1),groups=128)
        self.conv_3 = Residual(64,num_block=4,groups=128,kernel=(3,3),stride=(1,1),padding=(1,1))
        self.conv_34 = Depth_Wise(64,128,kernel=(3,3),stride=(2,2),padding=(1,1),groups=256)
        self.conv_4 = Residual(128,num_block=6,groups=256,kernel=(3,3),stride=(1,1),padding=(1,1))
        self.conv_45 = Depth_Wise(128,128,kernel=(3,3),stride=(2,2),padding=(1,1),groups=512)
        self.conv_5 = Residual(128,num_block=2,groups=256,kernel=(3,3),stride=(2,2),padding=(1,1))
        self.conv_6_sep = Conv_block(128,512,kernel=(1,1),stride=(1,1),padding=(0,0))
        self.conv_6_dw = Linear_block(512,512,groups=512,kernel=(7,7),stride=(1,1),padding=(0,0))
        self.conv_6_flatten = Flatten()
        self.linear = Linear(512,embedding_size,bias=False)
        self.bn = BatchNorm1d(embedding_size)
    def forward(self, x):
        out = self.conv1(x)
        out = self.conv2_dw(out)
        out = self.conv_23(out)
        out = self.conv_3(out)
        out = self.conv_34(out)
        out = self.conv_4(out)
        out = self.conv_45(out)
        out = self.conv_5(out)
        out = self.conv_6_sep(out)
        out = self.conv_6_dw(out)
        out = self.conv_6_flatten(out)
        out = self.linear(out)
        out = self.bn(out)
        return l2_norm(out)

class Arcface(Module):
    def __init__(self,embedding_size=512,classnum=51332,s=64,m=0.5):
        super(Arcface,self).__init__()
        self.classnum = classnum
        self.kernel = Parameter(torch.Tensor(embedding_size,classnum))
        self.kernel.data.uniform_(-1,1).renorm_(2,1,1e-5).mul_(1e5)
        self.m = m
        self.s = s
        self.cos_m = math.cos(m)
        self.sin_m = math.sin(m)
        self.mm = self.sin_m*m
        self.threshold = math.cos(math.pi - m)
    def forward(self, embedding,label):
        nB = len(embedding)
        kernel_norm = l2_norm(self.kernel,axis=0)
        cos_theta = torch.mm(embedding,kernel_norm)
        cos_theta = cos_theta.clamp(-1,1)
        cos_theta_2 = torch.pow(cos_theta,2)
        sin_theta_2 = 1 - cos_theta_2
        sin_theta = torch.sqrt(sin_theta_2)
        cos_theta_m = (cos_theta*self.cos_m-sin_theta*self.sin_m)
        cond_v = cos_theta - self.threshold
        cond_mask = cond_v <= 0
        keep_val = (cos_theta - self.mm)
        cos_theta_m[cond_mask] = keep_val[cond_mask]
        output = cos_theta*1.0
        idx_ = torch.arange(0,nB,dtype=torch.long)
        output[idx_,label] = cos_theta_m[idx_,label]
        output *= self.s
        return output

class Am_softmax(Module):
    def __init__(self,embedding_size=512,classnum=51332):
        super(Am_softmax,self).__init__()
        self.classnum = classnum
        self.kernel = Parameter(torch.Tensor(embedding_size,classnum))
        self.kernel.data.uniform_(-1,1).renorm_(2,1,1e-5).mul_(1e5)
        self.m = 0.35
        self.s = 30
    def forward(self, embbedings,label):
        kernel_norm = l2_norm(self.kernel,axis=0)
        cos_theta = torch.mm(embbedings,kernel_norm)
        cos_theta = cos_theta.clamp(-1,1)
        phi = cos_theta - self.m
        lable = label.view(-1,1)
        index = cos_theta.data *0.0
        index.scatter_(1,label.data.view(-1,1),1)
        index = index.byte()
        output = cos_theta * 1.0
        output[index] = phi[index]
        output *=self.s
        return output

class Softmax(Module):
    pass