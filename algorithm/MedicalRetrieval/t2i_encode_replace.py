@torch.no_grad()
def encode(cfg, text, image_path, model, tokenizer):
    device = next(model.parameters()).device

    if text is None:
        text = []
    elif isinstance(text, str):
        text = [text]

    if image_path is None:
        image_path = []
    elif isinstance(image_path, str):
        image_path = [image_path]

    text = [t for t in text if t is not None and str(t).strip() != ""]
    image_path = [p for p in image_path if p is not None and str(p).strip() != ""]

    text_feats = []
    img_feats = []

    if len(text) > 0:
        text_dataset = TextEmbedDataset(
            name="text_dataset",
            data_path=text,
            transform_config=cfg["transform"],
            tokenizer=tokenizer,
        )
        text_dataloader = DataLoader(
            text_dataset,
            collate_fn=text_dataset.collate_fn,
            **cfg["dataloader"]["test"]
        )

        for b in text_dataloader:
            feat, _, _ = model.encode_text(b["text_tokens"].to(device))
            text_feats.append(feat.detach().cpu())

    if len(image_path) > 0:
        image_dataset = ImageEmbedDataset(
            name="image_dataset",
            data_path=image_path,
            transform_config=cfg["transform"],
        )
        image_dataloader = DataLoader(
            image_dataset,
            collate_fn=ImageEmbedDataset.collate_fn,
            **cfg["dataloader"]["test"]
        )

        for b in image_dataloader:
            feat, _ = model.encode_image(b["images"].to(device))
            img_feats.append(feat.detach().cpu())

    text_feats = torch.cat(text_feats, dim=0) if len(text_feats) > 0 else []
    img_feats = torch.cat(img_feats, dim=0) if len(img_feats) > 0 else []

    return text_feats, img_feats
