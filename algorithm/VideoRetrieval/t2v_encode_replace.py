@torch.no_grad()
def encode(cfg, texts, video_paths, model, tokenizer):
    device = next(model.parameters()).device

    if texts is None:
        texts = []
    elif isinstance(texts, str):
        texts = [texts]

    if video_paths is None:
        video_paths = []
    elif isinstance(video_paths, str):
        video_paths = [video_paths]

    texts = [t for t in texts if t is not None and str(t).strip() != ""]
    video_paths = [p for p in video_paths if p is not None and str(p).strip() != ""]

    text_features = []
    video_features = []

    if len(texts) > 0:
        text_dataloader = mk_text_dataloader(
            dataset_name="text_dataloader",
            vis_format="video",
            anno_path=texts,
            vis_dir=None,
            cfg=cfg,
            tokenizer=tokenizer,
            mode="test"
        )

        for text_batch in text_dataloader:
            text_input_ids = text_batch["text_input_ids"].to(device, non_blocking=True)
            text_input_mask = text_batch["text_input_mask"].to(device, non_blocking=True)

            text_feature = model.forward_text(
                text_input_ids=text_input_ids,
                text_input_mask=text_input_mask,
            )
            text_features.append(text_feature.detach().cpu())

    if len(video_paths) > 0:
        video_dataloader = mk_video_dataloader(
            dataset_name="video_dataloader",
            vis_format="video",
            anno_path=None,
            vis_dir=video_paths,
            cfg=cfg,
            tokenizer=tokenizer,
            mode="test"
        )

        for video_batch in video_dataloader:
            video = video_batch["video"].to(device, non_blocking=True)

            video_feature = model.forward_video(video)
            video_features.append(video_feature.detach().cpu())

    text_features = torch.cat(text_features, dim=0) if len(text_features) > 0 else []
    video_features = torch.cat(video_features, dim=0) if len(video_features) > 0 else []

    return text_features, video_features
