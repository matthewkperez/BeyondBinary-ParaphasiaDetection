"""Library implementing quaternion-valued linear transformation.

Authors
 * Titouan Parcollet 2020
"""

import torch
import logging
from speechbrain.nnet.quaternion_networks.quaternion_ops import (
    quaternion_linear,
    check_quaternion_input,
    quaternion_linear_autograd,
)

logger = logging.getLogger(__name__)

class QuaternionLinear(torch.nn.Module):
    """ This function implements a fully connected quaternion-valued
        linear layer: y = Wx + b. y, W, x and b are thus quaternion
        numbers. A quaternion number is written as: r + xi + yj + zk.
        A tensor of quaternion numbers x = [batch, 32] can be understood as
        [batch, 0:7] = R, [batch, 8:15] = Xi, [batch, 16:23] = Yi, and
        [batch, 24:31] = Xi. Thus the features dimension is cut in four
        (must be dividible by 4).

    Arguments
    ---------
    n_neurons : int
        it is the number of output neurons (i.e, the dimensionality of the
        output). Please note that these are quaternion-valued neurons. If 256
        neurons are specified, the output dimension will be 1024.
    input_shape : tuple
        Expected size of the input.
    bias : bool
        if True, the additive bias b is adopted.
    init_criterion: str , optional
        Default: he.
        (glorot, he).
        This parameter controls the initialization criterion of the weights.
        It is combined with weights_init to build the initialization method of
        the quaternion-valued weights.
    weight_init: str, optional
        Default: quaternion.
        (quaternion, unitary).
        This parameter defines the initialization procedure of the
        complex-valued weights. "quaternion" will generate quaternion-valued
        weights following the init_criterion and the quaternion  polar form.
        "unitary" will normalize the weights to lie on the unit circle.
        More details in: "Quaternion recurrent neural networks", Parcollet T.
    autograd: bool, optional
        Default: True.
        When True, the default PyTorch autograd will be used. When False, a
        custom backpropagation will be used, reducing by a factor 3 to 4 the
        memory consumption. It is also 2x slower.


    Example
    -------
    >>> inputs = torch.rand(10, 50, 40)
    >>> lin = QuaternionLinear(n_neurons=100, input_shape=inputs.shape)
    >>> output = lin(inputs)
    >>> output.shape
    torch.Size([10, 50, 400])
    """

    def __init__(
        self,
        n_neurons,
        input_shape,
        bias=True,
        init_criterion="glorot",
        weight_init="quaternion",
        autograd=True
    ):
        super().__init__()
        self.n_neurons = n_neurons
        self.bias = bias
        self.init_criterion = init_criterion
        self.weight_init = weight_init

        # Check the quaternion_valued form of the input
        check_quaternion_input(input_shape)

        # Computing the complex dimensionality of the input
        self.in_features = input_shape[-1] // 4
        self.out_features = self.n_neurons

        if autograd:
            self.linear = quaternion_linear_autograd(
                self.in_features,
                self.out_features,
                self.bias,
                self.init_criterion,
                self.weight_init,
            )
        else:
            self.linear = quaternion_linear(
                self.in_features,
                self.out_features,
                self.bias,
                self.init_criterion,
                self.weight_init,
            )

    def forward(self, x):
        """Returns the linear transformation of input tensor.

        Arguments
        ---------
        x : torch.Tensor
            input to transform linearly.
        """
        wx = self.linear(x)

        return wx
