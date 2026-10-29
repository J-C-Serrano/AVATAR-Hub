"""Lossless speed-up of transformers' Whisper word timestamps on a shared GPU.
WhisperGenerationMixin._postprocess_outputs splits the generate outputs per batch item and calls .cpu() on every
attention tensor of every decoding step and layer (~250 calls for one short clip); _stack_split_outputs then moves
them all back to the GPU. Each .cpu() is a GPU sync, and with several processes time-sharing the GPU each sync waits
for this process's next time slice: 39 s of a 40 s word-timestamp call (plain transcription: 0.5 s).
install() keeps those tensors on the GPU (only the .cpu() calls made by split_by_batch_index; every other .cpu(),
e.g. the DTW input, is untouched). The pipeline moves its final outputs to the CPU itself, so results are identical.
usage: import whisper_fast; whisper_fast.install()   (before the first ASR call)"""
import sys
import torch

_cpu = torch.Tensor.cpu


def _keep_on_gpu(self, *a, **k):
    if self.is_cuda and sys._getframe(1).f_code.co_name == "split_by_batch_index":
        return self
    return _cpu(self, *a, **k)


def install():
    from transformers.models.whisper import generation_whisper as G
    orig = G.WhisperGenerationMixin._postprocess_outputs
    if getattr(orig, "_whisper_fast", False):
        return

    def _postprocess_outputs(self, *a, **k):
        torch.Tensor.cpu = _keep_on_gpu
        try:
            return orig(self, *a, **k)
        finally:
            torch.Tensor.cpu = _cpu
    _postprocess_outputs._whisper_fast = True
    G.WhisperGenerationMixin._postprocess_outputs = _postprocess_outputs
