# Warframe Nutcracker
帮助星际仓鼠们轻松管理部件库存！
以及自动在挂机生存时候开核桃
打包好的 exe 文件可前往 Action 页面下载。

## Ducats OCR
该工具可扫描指定文件夹中的所有截图，并生成仓库物品的价格信息，包括白金价格和杜卡德金币。生成结果会按照杜卡德/白金的性价比从高到低排列。
白金价格基于 Warframe Market 当前在线卖家前10名的平均值。
扫描完成后，双击或右键点击第一列的物品名称即可复制，方便清仓操作。

## Survive
自动在挂机生存时开核桃
json文件clickx,y为第一个核桃的xy坐标（用ahk的windowspy，打开船上的遗物界面，鼠标移到第一行第二个遗物图标中间）
scale为Windows的显示scale
nutFlag为false时，只检测死亡情况不开核桃，用于挂机刷材料


# 截图范例
![alt text](https://github.com/requiem2017/WarframeDucatsOCR/blob/main/example/test.png)
# UI
![alt text](https://github.com/requiem2017/WarframeDucatsOCR/blob/main/example/UI.png)
# TODO List
- [ ] WF market 自动挂前x个值钱物品
  - [ ] 只挂重复物品
- [ ] 识别开核桃最值钱物品
- [ ] 仓库扫描+输入想刷甲，计算光体阿耶期望
- [ ] 识别聊天栏WTS和WF market差价
- [ ] 紫卡交易历史
- [ ] 物品交易历史
