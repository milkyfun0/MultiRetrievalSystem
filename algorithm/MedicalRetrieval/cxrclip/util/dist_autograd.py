import torch
import torch.distributed as dist


def DistAutogradAllGatherFunction(partial=False):
    class F(torch.autograd.Function):
        @staticmethod
        def forward(ctx, input):
            # 确保输入张量是连续的
            ctx.save_for_backward(input)
            world_size = dist.get_world_size()
            output = [torch.zeros_like(input) for _ in range(world_size)]

            # 执行 all_gather 操作，确保 output 是连续的
            dist.all_gather(output, input)

            for i in range(world_size):
                output[i] = output[i]

            return tuple(output)

        @staticmethod
        def backward(ctx, *grads):
            (input,) = ctx.saved_tensors
            grad_out = torch.zeros_like(input)
            grads = [grad.contiguous() for grad in grads]
            if partial:
                grad_out[:] = grads[dist.get_rank()]
            else:
                # 执行 reduce_scatter 操作，确保 grad_out 是连续的
                dist.reduce_scatter(grad_out, list(grads), dist.ReduceOp.SUM)

            return grad_out

    return F
