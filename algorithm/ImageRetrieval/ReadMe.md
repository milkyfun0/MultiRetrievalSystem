

初始化 pos和conv比较重要 --- 浅层特征

## **ViT  8M**  freeze 1/2 = 3.2M 

```json
sgd:
  lr: 0.0005
  weight_decay: "5e-4"
  momentum: 0.9 # sgd default
loss:
  margin: 0.5
  T: 0.1
  alpha: 2
  beta: 1
  gamma: 0.5
train:
  epoch: 50
  batch_size: 256
  num_works: 4

NWEP_RESISC45 0.965
AID: 0.9727
UCMD: 0.9856


128 total loss: 0.95
```

## **ViT  38M**  freeze 1/2 

```json
sgd:
  lr: 0.0001
  weight_decay: "5e-4"
  momentum: 0.9 # sgd default

loss:
  margin: 0.5
  T: 0.1
  alpha: 2
  beta: 1
  gamma: 0.5

NWEP_RESISC45 0.976
AID: 0.9871
UCMD: 0.9933
```

## base distill

### not change

```json
sgd:
  lr: 0.0005
  weight_decay: "1e-4"
  momentum: 0.9 # sgd default

loss:
  margin: 0.6
  T: 0.1
  alpha: 1
  beta: 1
  gamma: 0.5
train:
  epoch: 40
  batch_size: 128
  num_works: 4

loss: 2.16
map: 0.9666
```

### add 2 layer

```json
sgd:
  lr: 0.0005
  weight_decay: "1e-4"
  momentum: 0.9 # sgd default

loss:
  margin: 0.6
  T: 0.5
  alpha: 1
  beta: 1
  gamma: 0.5

train:
  epoch: 40
  batch_size: 128
  num_works: 4

loss: 4.11
MAP: 0.954
```

### add adapter

```json
sgd:
  lr: 0.0005
  weight_decay: "1e-4"
  momentum: 0.9 # sgd default


loss:
  margin: 0.6
  T: 0.1
  alpha: 1
  beta: 1
  gamma: 0.5

train:
  epoch: 40
  batch_size: 128
  num_works: 4

loss: 2.16
map: 0.957
```

## base cnn

