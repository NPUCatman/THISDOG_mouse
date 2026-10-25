# 这狗 · macOS 鼠标指针

这是适用于 **Mousecape** 的静态光标主题，依据小红书作者「你自己做吧」的展示图还原。图形、配色与 Windows 版一致；没有取得原作动画，因此本版不含动画。

## 选择文件

- **这狗_mac.cape**：标准版，32 pt 画布，建议先试用。
- **这狗_mac_大号.cape**：大号版，48 pt 画布。
- **备选/**：5 个不同造型的正常箭头主题，以及正常箭头的矢量重绘主题。每个 `.cape` 都是完整主题，可以直接导入、应用；重绘版与原展示图有细微差异。
- **预览.png**：全部造型、浅深背景与两种大小的总览。
- **这狗_mac.zip**：可直接复制到 Mac 后解压的整套文件。

每个 `.cape` 都内嵌 1× / 2× 透明 PNG，自包含且不依赖父文件夹。32 pt 版内嵌 32 / 64 px 图像，48 pt 版内嵌 48 / 96 px 图像；2× 图像用于 Retina 显示。尺寸指画布，角色本身会保留透明边距。放大不会增加原展示图中没有的细节。

Windows 的手写、位置选择和人物选择没有对应的 macOS 光标角色。手写 PNG 作为编辑素材保留，不会随主题应用。

## 在 Mac 上使用

1. 从 [Mousecape 官方发行页](https://github.com/alexzielenski/Mousecape/releases/latest) 下载适合你的 macOS 的版本，将应用放入“应用程序”并打开。
2. 若 Mousecape 提示需要辅助工具，在应用菜单选择 **Mousecape → Install Helper Tool**，按照应用提示完成。
3. 应用前，在 Mousecape 中记下当前已应用的方案。若是自定义方案，选中它，用 **Capes → Show in Finder** 找到原 `.cape` 文件并另外复制留存。
4. 双击 **这狗_mac.cape** 导入；也可以在 Mousecape 中选择 **File → Import Cape** 后打开该文件。
5. 在主题列表选中“这狗”，右键选择 **Apply**；菜单栏也可使用 **Capes → Apply Cape**。需要更大时，导入并应用大号版。备选主题的操作相同。

Mac 导入后由 Mousecape 管理主题。无需运行本目录的 Python 脚本，也无需安装 Python。

## 恢复与兼容性

恢复之前的自定义方案：在 Mousecape 选择原方案，再应用；若原方案已不在列表中，先导入备份的 `.cape`。恢复系统默认光标：使用 **Capes → Restore Defaults**。上述菜单名称依据 Mousecape 官方源代码核实，不同发行版的界面可能略有不同。

本包在 Windows 上完成格式、图像、尺寸和热点等结构校验，**尚未在真实 Mac 上应用测试**。主题覆盖范围受 Mousecape、macOS 版本以及各应用自身实现影响；部分应用的自定义光标可能保留原样，不保证所有 macOS 版本都能使用。实际效果以你的 Mac 为准。

## 文件与来源

`assets/` 保留透明 PNG，`manifest.json` 记录角色映射与热点，`tools/` 保存重新生成和校验用的脚本。它们便于继续编辑；直接使用只需导入 `.cape` 文件。

原设计与展示：[这狗鼠标指针皮肤做好啦！！好可爱🥰](https://www.xiaohongshu.com/discovery/item/696b5835000000000e00c7a4)，作者「你自己做吧」。原角色、原图及皮肤设计的权利归各自权利人。本包是依据展示图制作的静态还原版，不是作者发布的原始光标文件。

Mousecape：[官方仓库](https://github.com/alexzielenski/Mousecape) · [官方菜单定义](https://github.com/alexzielenski/Mousecape/blob/master/Mousecape/Mousecape/Base.lproj/MainMenu.xib)
