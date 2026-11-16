# 特徕福信息流 A 版封面

`telaifu-coverA` 是一个 Codex Skill。提供封面标题和两张配图，即可生成一张 **1080 × 1920（9:16）PNG**。A 版使用深蓝星空、奶金色立体标题、白边相框和随标题变化的四字贴纸。

## 成片示例

<a href="references/approved-cover.png"><img src="references/approved-cover.png" width="320" alt="特徕福招牌搭对料 A 版封面"></a>

这张封面以夜景门店为主图、白天门店为副图，贴纸为「招牌对料」，标题放大铺满顶部且金笔刷可见。[查看这张封面的制作记录](references/approved-workflow.md)。

## 安装

在 Windows PowerShell 中，登录有仓库访问权限的 GitHub 账号，然后将仓库克隆到 Codex 的个人 Skills 目录。

~~~powershell
$codexDir = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$skillsDir = Join-Path $codexDir 'skills'
New-Item -ItemType Directory -Path $skillsDir -Force | Out-Null
git clone https://github.com/Valentina-Qiao/telaifu-coverA.git (Join-Path $skillsDir 'telaifu-coverA')
~~~

也可以下载仓库，解压后把包含 `SKILL.md` 的文件夹命名为 `telaifu-coverA`，放入同一目录。

## 使用

在 Codex 里说「制作特徕福信息流 A 版封面」，或输入 `$telaifu-coverA`。附上标题和照片，例如：

> 制作特徕福信息流 A 版封面，标题为「特徕福招牌搭对料客源忘不了」。第一张夜景门店放左上，第二张白天门店放右下。

默认按配图顺序入框。也可以指定主副图、标题换行和四字贴纸文案。

## 工作流程

1. 用 ImageGen 按[字形参考](assets/headline-style-reference.png)在**纯绿幕背景 RGB(0,255,0)** 上生成主标题，逐字核对，再用 `scripts/key_green.py` 抠成透明 PNG。ImageGen 无法输出真实透明，直接请求「透明背景」会得到棋盘格图并残留灰楔/斑点，务必走绿幕流程。随包字稿可直接复用。
2. 从标题提炼贴题的四字候选，由脚本随机选出一个，或使用你指定的短语。
3. 把标题、贴纸和原照片合成到固定模板中，按可见内容垂直居中。调整取景时复用已确认的标题和贴纸。标题偏小时可用 `headline_max_size`、`headline_bottom` 参数放宽，见 [SKILL.md](SKILL.md#标题尺寸避免标题偏小)。
4. 检查成片：标题文字逐字正确、金笔刷在第二行下方可见、照片主体在框内、上下留白均衡，最后导出 PNG。放大标题后若金笔刷被盖住，用 `gold_brush_pos` 下移，见 [SKILL.md](SKILL.md#金色笔刷消失放大标题的连带问题)。

本地合成需要带 Pillow 和 NumPy 的 Python。直接运行脚本时，请参考 [SKILL.md 中的渲染参数](SKILL.md#渲染参数)。

## 常见问题

这三个问题都已在 skill 里沉淀为结构化方案，遇到时按对应章节处理：

| 问题 | 处置 | 详见 |
| --- | --- | --- |
| 标题抠图有灰色楔形 / 深灰斑点 | 绿幕生成 + 强制字面全不透明，不要用「填充空洞」式抠图 | [绿幕生成与抠图](SKILL.md#绿幕生成与抠图必做) |
| 标题偏小、没铺满顶部区域 | 调 `headline_max_size`、`headline_bottom` | [标题尺寸](SKILL.md#标题尺寸避免标题偏小) |
| 放大标题后金笔刷消失 | 调 `gold_brush_pos` 把笔刷下移到第二行下方 | [金色笔刷消失](SKILL.md#金色笔刷消失放大标题的连带问题) |
