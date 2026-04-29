import ast
import json
import random
from typing import Dict, List

import numpy as np
import pandas as pd
import torch
from nltk import tokenize, sent_tokenize
from PIL import Image
from torch.utils.data.dataset import Dataset

from cxrclip.data.data_utils import load_transform, transform_image
from cxrclip.prompt.prompts import generate_report_from_labels


class ImageTextDataset(Dataset):
    def __init__(
            self,
            tokenizer,
            name: str,
            data_path: str,
            split: str,
            text_max_length: int = 150,
            text_sampling: str = "random",
            loss_config: Dict = None,
            transform_config: Dict = None,
            prompt_from_json: bool = False,
            data_frac: float = 1.0,
            num_negs: int = 0,
            normalize: str = "huggingface",
            **kwargs
    ):
        super().__init__()
        self.name = name
        self.split = split
        self.text_max_length = text_max_length
        self.text_sampling = text_sampling
        self.data_frac = data_frac
        self.num_negs = num_negs
        self.normalize = normalize

        self.tokenizer = tokenizer
        print(split, transform_config)
        self.image_transforms = load_transform(split=split, transform_config=transform_config)
        # 加载spacy模型用于短语识别
        # self.nlp = spacy.load("en_core_web_sm")

        if prompt_from_json:
            with open("datasets/train_prompts_all.json") as f:
                self.prompt_json = json.load(f)
        else:
            self.prompt_json = False

        assert data_path.endswith(".csv")

        self.df = pd.read_csv(data_path)
        if data_frac < 1.0:
            self.df = self.df.sample(frac=self.data_frac, random_state=1, ignore_index=True)

        self.loss_config = {k: v for k, v in loss_config.items()}

        self.image_view_aug = True
        self.image_aug_other_image = True
        self.image_aug_transforms = self.image_transforms
        self.has_backtranslated = hasattr(self.df, "text_augment")
        # self.bleu = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
        

        # print(self.__len__(), "=============")

    def __len__(self):
        return len(self.df)

    def __getitem__(self, index):
        if hasattr(self.df, "AP"):  # AP / PA / Lateral
            try:
                view_list = ast.literal_eval(self.df["view"][index])
            except Exception:
                view_list = [self.df["view"][index]]

            if len(view_list) > 2:
                view_list = np.random.choice(view_list, size=2, replace=False)
                image_path_list = []
                for view in view_list:
                    try:
                        image_path_list = ast.literal_eval(self.df[view][index])
                    except Exception:
                        image_path_list = [self.df[view][index]]
                    image_path = np.random.choice(image_path_list, size=1)[0]
                    image_path_list.append(image_path)

            else:
                if len(view_list) == 1:
                    tag = view_list[0]
                else:
                    tag = "image"

                try:
                    image_path_list = ast.literal_eval(self.df[tag][index])
                except Exception:
                    image_path_list = [self.df[tag][index]]

                if self.split == "train":
                    if self.image_aug_other_image and len(image_path_list) > 1:
                        image_path_list = np.random.choice(image_path_list, size=2, replace=False)
                    else:
                        image_path_list = np.random.choice(image_path_list, size=1)
        else:
            try:
                image_path_list = ast.literal_eval(self.df["image"][index])
            except Exception:
                image_path_list = [self.df["image"][index]]

        image_original = Image.open(image_path_list[0]).convert("RGB")
        # image_original = Image.open(image_path_list[0].replace("/home/sx1025/Medical", "../")).convert("RGB")
        image = transform_image(self.image_transforms, image_original, normalize=self.normalize)

        if self.image_view_aug:
            if len(image_path_list) > 1:
                image_original = Image.open(image_path_list[1]).convert("RGB")

            image_view = transform_image(self.image_aug_transforms, image_original, normalize=self.normalize)

        # Get Text or Prompt
        if hasattr(self.df, "text"):
            try:
                text_list = ast.literal_eval(self.df["text"][index])
            except Exception:
                text_list = self.df["text"][index]

            if self.has_backtranslated:
                try:
                    text_aug_list = ast.literal_eval(self.df["text_augment"][index])
                except Exception:
                    text_aug_list = self.df["text_augment"][index]

            if len(text_list) >= 2:
                indexes = np.random.randint(len(text_list), size=2)  # Multiple section
                text = text_aug_list[indexes[0]] if random.random() < 0.5 and self.has_backtranslated else text_list[
                    indexes[0]]
                text2 = text_aug_list[indexes[1]] if random.random() < 0.5 and self.has_backtranslated else text_list[
                    indexes[1]]

            else:
                if random.random() < 0.5:
                    text = text_list[0]
                    text2 = text_aug_list[0] if self.has_backtranslated else text_list[0]
                else:
                    text = text_aug_list[0] if self.has_backtranslated else text_list[0]
                    text2 = text_list[0]

            if self.split == "train":  # Text shuffle augment
                for _text in [text, text2]:
                    _text_list = tokenize.sent_tokenize(_text, language="english")
                    random.shuffle(_text_list)
                    _text = " ".join(_text_list)

        # Get Two Prompts per sample.
        elif hasattr(self.df, "text_label"):
            labels = ast.literal_eval(self.df["text_label"][index])
            text = generate_report_from_labels(
                labels, self.prompt_json, deterministic=(self.split != "train"), num_negs=self.num_negs, name=self.name
            )
            text2 = generate_report_from_labels(
                labels, self.prompt_json, deterministic=(self.split != "train"), num_negs=self.num_negs, name=self.name
            )
        else:
            raise AttributeError("There is no report column in DataFrame.")

        out = {"image": image, "image_view": image_view, "text": text, "text2": text2, 'image_path_list': image_path_list}

        return out
    
    
    def _extract_phrase_spans(self, input_ids):
        """识别短语边界并返回token级别的起止位置"""
        text = self.tokenizer.decode(input_ids, skip_special_tokens=True)
        doc = self.nlp(text)
        
        # 获取短语边界
        phrases = []
        for chunk in doc.noun_chunks:
            # 将字符偏移量转换为token索引
            start_char = chunk.start_char
            end_char = chunk.end_char
            
            # 找到对应的token位置
            start_token = None
            end_token = None
            current_pos = 0
            for idx, token_id in enumerate(input_ids):
                token = self.tokenizer.decode([token_id])
                token_len = len(token)
                
                if current_pos <= start_char < current_pos + token_len:
                    start_token = idx
                if current_pos < end_char <= current_pos + token_len:
                    end_token = idx + 1  # 结束位置是开区间
                    break
                current_pos += token_len
                
            if start_token is not None and end_token is not None:
                phrases.append((start_token, end_token))
        
        return phrases

    def text_masked_language_modeling(self, text, mask_ratio=0.15, k_sample=1):
        mask_token_id = self.tokenizer.mask_token_id
        
        # 获取原始输入
        input_ids = text["input_ids"]
        attention_mask = text["attention_mask"]
        token_type_ids = text.get("token_type_ids", None)  # 可选字段
        
        b, context_length = input_ids.shape
        
        # 初始化最终掩码矩阵 (b, k_sample, seq_len)
        phrase_mask_matrix = torch.ones(
            b, k_sample, context_length, 
            dtype=torch.long, device=input_ids.device)
        
        # 特殊token掩码 (CLS, SEP, PAD等)
        special_tokens_mask = torch.zeros_like(input_ids, dtype=torch.bool)
        for special_id in self.tokenizer.all_special_ids:
            special_tokens_mask |= (input_ids == special_id)
        
        # 处理每个样本
        for i in range(b):
            valid_length = attention_mask[i].sum().item()
            sample_ids = input_ids[i, :valid_length].cpu().numpy()
            
            # 步骤1: 提取短语边界
            try:
                phrase_spans = self._extract_phrase_spans(sample_ids)
            except Exception as e:
                print(f"Phrase extraction failed: {e}")
                phrase_spans = []
            
            # 步骤2: 计算目标掩码token数
            num_valid_tokens = valid_length - special_tokens_mask[i, :valid_length].sum().item()
            target_masked_tokens = int(num_valid_tokens * mask_ratio + 0.5)
            
            # 步骤3: 选择要掩码的短语
            random.shuffle(phrase_spans)  # 随机排序短语
            
            # 存储当前样本所有k_sample的掩码位置
            sample_masks = []
            
            for k in range(k_sample):
                # 当前掩码版本的掩码矩阵 (初始全1表示不掩码)
                mask_vector = torch.ones(context_length, dtype=torch.long, device=input_ids.device)
                current_masked = 0
                
                # 尝试用短语掩码
                for start, end in phrase_spans:
                    if current_masked >= target_masked_tokens:
                        break
                    
                    # 检查是否包含特殊token
                    if special_tokens_mask[i, start:end].any():
                        continue
                    
                    # 计算短语长度
                    phrase_length = end - start
                    
                    # 应用掩码
                    mask_vector[start:end] = 0
                    current_masked += phrase_length
                
                # 如果短语掩码不足，补充随机掩码
                if current_masked < target_masked_tokens:
                    additional_needed = target_masked_tokens - current_masked
                    valid_positions = [
                        idx for idx in range(valid_length) 
                        if mask_vector[idx] == 1 and not special_tokens_mask[i, idx]
                    ]
                    
                    if valid_positions:
                        # 随机选择补充位置
                        num_to_mask = min(additional_needed, len(valid_positions))
                        random.shuffle(valid_positions)
                        for idx in valid_positions[:num_to_mask]:
                            mask_vector[idx] = 0
                
                sample_masks.append(mask_vector)
            
            # 将k_sample个掩码版本存入矩阵
            for k, mask_vec in enumerate(sample_masks):
                phrase_mask_matrix[i, k] = mask_vec
        
        # 应用掩码
        input_ids_masked = (
            input_ids.unsqueeze(1) * phrase_mask_matrix +
            (1 - phrase_mask_matrix) * mask_token_id
        )
        
        attention_mask_masked = attention_mask.unsqueeze(1) * phrase_mask_matrix
        
        # 处理token_type_ids (如果有)
        if token_type_ids is not None:
            token_type_ids_masked = token_type_ids.unsqueeze(1).expand(-1, k_sample, -1)
        else:
            token_type_ids_masked = None
        
        # 展平k_sample维度
        input_ids_masked = input_ids_masked.view(b * k_sample, context_length)
        attention_mask_masked = attention_mask_masked.view(b * k_sample, context_length)
        
        # 确保长度一致
        assert input_ids_masked.shape == attention_mask_masked.shape
        
        # 构建返回字典
        result = {

            "input_ids": input_ids_masked,
            "attention_mask": attention_mask_masked,
        }
        
        if token_type_ids_masked is not None:
            token_type_ids = token_type_ids.unsqueeze(1).expand(-1, k_sample, -1) 
            token_type_ids_masked = token_type_ids_masked.reshape(b * k_sample, context_length)
            result["token_type_ids"] = token_type_ids_masked
        
        return result

    def collate_fn(self, instances: List):
        image_path =  list([ins["image_path_list"] for ins in instances])
        images = torch.stack([ins["image"] for ins in instances], dim=0)
        texts = list([ins["text"] for ins in instances])
        # text_tokens = self.tokenizer(
        #     texts, padding=True, truncation=True, return_tensors="pt", max_length=self.text_max_length
        # )
        text_batch_length = torch.zeros((len(texts), 1), dtype=torch.long, device=images.device)
        text_sentences = []
        for idx, text in enumerate(texts):
            sentences = sent_tokenize(text)
            sentences = random.sample(sentences, 1)
            text_sentences.extend(sentences)
            text_batch_length[idx] = len(sentences)
        text_tokens = self.tokenizer(
            text_sentences, padding=True, truncation=True, return_tensors="pt", max_length=self.text_max_length
        )
        # print(text_tokens.keys())
        # 8471179e-096f140b-40344323-2d36d592-199b26cf. 应用phrase-level masking
        # text_token_mask = self.text_masked_language_modeling(
        #     text_tokens,  # 传入正确的tokenizer输出格式
        #     mask_ratio=0.3,
        #     k_sample=8471179e-096f140b-40344323-2d36d592-199b26cf
        # )
        # text_tokens["input_ids"] = text_token_mask["input_ids"]
        # text_tokens["attention_mask"] = text_token_mask["attention_mask"]
        # text_tokens["token_type_ids"] = text_token_mask["token_type_ids"]

        
        sentence_sims = torch.zeros(len(texts), len(texts), dtype=torch.float32)
        for i in range(len(texts)):
            # sentence_sims[i][i] = 1 
            for j in range(len(texts)):
                sentence_sims[i][j] = self.bleu([texts[i]], [[texts[j]]])
                # print(self.bleu.score(texts[i], texts[j]))
                # sentence_sims[i][j] = self.bleu.score(texts[i], texts[j])["rougeL"].fmeasure

        # texts2 = list([ins["text2"] for ins in instances])
        # text_tokens2 = self.tokenizer(
        #     texts2, padding=True, truncation=True, return_tensors="pt", max_length=self.text_max_length
        # )

        # image_views = torch.stack([ins["image_view"] for ins in instances], dim=0)

        batch = {
            "images": images,
            'image_path': image_path,
            # "image_views": image_views,
            "texts": texts,
            # "texts2": texts2,
            "text_tokens": text_tokens,
            # "text_tokens2": text_tokens2,
            "sentence_sims": sentence_sims,
        }

        return batch
