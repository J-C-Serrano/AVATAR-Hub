FROM avatar-chatterbox:p0
# LoRA fine-tuning of Chatterbox multilingual T3 (peft, Apache-2.0)
RUN pip freeze | grep -iE '^(torch|torchaudio|numpy|transformers)==' > /tmp/c.txt; pip install --no-cache-dir -c /tmp/c.txt peft tensorboard 2>&1 | tail -1
RUN pip uninstall -y torchao
