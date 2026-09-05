"""Fine-tuning script for Medical Grounded RAG with PEFT LoRA / QLoRA.

Supports:
- Ministral 3B / Mistral 7B / Llama 3.2 models
- 4-bit / 8-bit QLoRA and full 16-bit LoRA
- SFTTrainer with chat template formatting
- Model saving, evaluation metrics, and adapter checkpointing
"""
import argparse
import json
import os
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).parent
TRAIN_DATA = ROOT / "data" / "processed" / "train_sft.jsonl"
VAL_DATA = ROOT / "data" / "processed" / "val_sft.jsonl"
OUTPUT_MODEL_DIR = ROOT / "models" / "ministral_synthea_lora"


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Medical RAG model using LoRA / QLoRA")
    parser.add_argument("--model-id", type=str, default="mistralai/Ministral-3-3B-Instruct-2512", help="Hugging Face model ID")
    parser.add_argument("--train-data", type=Path, default=TRAIN_DATA, help="Path to train_sft.jsonl")
    parser.add_argument("--val-data", type=Path, default=VAL_DATA, help="Path to val_sft.jsonl")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_MODEL_DIR, help="Output directory for saved adapter")
    parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=2, help="Per-device batch size")
    parser.add_argument("--grad-accum", type=int, default=8, help="Gradient accumulation steps")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank dimension")
    parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA scaling alpha")
    parser.add_argument("--max-seq-len", type=int, default=1024, help="Max sequence length")
    parser.add_argument("--use-4bit", action="store_true", default=True, help="Use 4-bit quantization (QLoRA)")
    args = parser.parse_args()

    print("=====================================================")
    print("   Medical RAG Grounded Model Fine-Tuning (LoRA)     ")
    print("=====================================================")
    print(f"Base Model: {args.model_id}")
    print(f"Train Dataset: {args.train_data}")
    print(f"Validation Dataset: {args.val_data}")
    print(f"Output Directory: {args.output_dir}")
    print(f"LoRA config: r={args.lora_r}, alpha={args.lora_alpha}")
    print("-----------------------------------------------------")

    # Check CUDA availability
    if not torch.cuda.is_available():
        print("[!] Warning: CUDA GPU not detected. Training on CPU or via Google Colab T4/A100 is recommended.")
        print("    You can run the provided 'colab_qlora_ministral.ipynb' on Google Colab for free GPU acceleration.")

    try:
        from datasets import Dataset
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            TrainingArguments,
        )
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from trl import SFTTrainer
    except ImportError as e:
        print(f"[X] Missing required packages: {e}")
        print("    Install them using: pip install transformers datasets peft trl bitsandbytes accelerate")
        sys.exit(1)

    if not args.train_data.exists():
        print(f"[X] Training data not found at {args.train_data}. Running create_finetuning_dataset.py first...")
        os.system(f"python {ROOT / 'create_finetuning_dataset.py'}")

    print("[1/5] Loading datasets...")
    train_records = [json.loads(line) for line in args.train_data.read_text(encoding="utf-8").splitlines() if line.strip()]
    val_records = [json.loads(line) for line in args.val_data.read_text(encoding="utf-8").splitlines() if line.strip()]

    print(f"      Loaded {len(train_records)} training samples, {len(val_records)} validation samples.")

    print(f"[2/5] Loading tokenizer for {args.model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def format_for_sft(sample):
        # Apply model chat template
        formatted_text = tokenizer.apply_chat_template(
            sample["messages"],
            tokenize=False,
            add_generation_prompt=False
        )
        return {"text": formatted_text}

    train_ds = Dataset.from_list(train_records).map(format_for_sft)
    val_ds = Dataset.from_list(val_records).map(format_for_sft)

    print("[3/5] Initializing Model with Quantization & LoRA...")
    if args.use_4bit and torch.cuda.is_available():
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        )
        device_map = "auto"
    else:
        bnb_config = None
        device_map = None

    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        quantization_config=bnb_config,
        device_map=device_map,
        trust_remote_code=True,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    )

    if args.use_4bit and torch.cuda.is_available():
        model = prepare_model_for_kbit_training(model)

    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    print("[4/5] Configuring Training Arguments...")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        warmup_ratio=0.03,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=2,
        fp16=torch.cuda.is_available() and not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        dataset_text_field="text",
        max_seq_length=args.max_seq_len,
        args=training_args,
    )

    print("[5/5] Starting Fine-Tuning...")
    trainer.train()

    print(f"[✓] Training complete. Saving LoRA adapter to {args.output_dir}...")
    trainer.save_model(str(args.output_dir))
    tokenizer.save_pretrained(str(args.output_dir))
    print(f"[✓] Adapter successfully saved at: {args.output_dir}")


if __name__ == "__main__":
    main()
