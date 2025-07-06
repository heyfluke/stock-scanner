# 在 Synology NAS 上通过图形界面部署 Stock Scanner (新手友好，内网访问)

本文档为不熟悉 Docker 或命令行的用户提供了一份详细的图形化部署指南。我们将使用 Synology DSM 的 **Container Manager** 和 **File Station** 来完成所有操作。熟悉`docker`和`docker-compose`的用户完全可跳过本文。

## 准备工作

### 1. 安装套件
确保您已在 Synology 套件中心安装了以下两个套件：
*   `Container Manager`
*   `文本编辑器`

### 2. 创建共享文件夹
为了方便管理，我们建议创建一个专门用于存放 Docker 应用的共享文件夹。
*   打开 `控制面板` -> `共享文件夹`。
*   点击 `新增`，创建一个名为 `/volume1/docker/stock-scanner`，BTW，你以后创建别的项目的主目录也可以位于`docker`目录下。

## 部署步骤

### 1. 准备项目文件
1. 将本项目的`docker-composer.yml`（或者更简单的从`docker-composer.simple.yml`中摘取如下部分）作为配置文件（保存在本地或者上传在NAS的`stock-scanner`目录）：

```YAML
version: '3.8'

services:
  app:
    image: heyfluke/stock-scanner:latest
    container_name: stock-scanner-app
    ports:
      - "8888:8888"
    environment:
      - API_KEY=${API_KEY}
      - API_URL=${API_URL}
      - API_MODEL=${API_MODEL}
      - API_TIMEOUT=${API_TIMEOUT}
      - LOGIN_PASSWORD=${LOGIN_PASSWORD}
      - ANNOUNCEMENT_TEXT=${ANNOUNCEMENT_TEXT}
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped
    networks:
      - stock-scanner-network

networks:
  stock-scanner-network:
    driver: bridge 
```

3. 在`/volume1/docker/stock-scanner`目录下面创建一个`.env`文件，包含所需环境变量（其实也可以跳过这个步骤，在后续部署成功的网页中设置）

```
API_KEY=your_api_key
API_URL=https://api.example.com
API_MODEL=your_model
API_TIMEOUT=30
LOGIN_PASSWORD=your_password
ANNOUNCEMENT_TEXT=your_text
```

### 2. 创建项目（对应docker-compose配置文件）
1.  打开`Container Manager`，找到`Project`。
3.  点击 `Create` 按钮。
4.  在创建项目向导中，填写以下信息：
    *   **项目名称**: `stock-scanner`
    *   **源**: 选择 `创建`
    *   **路径**: 点击 `选择文件夹` 按钮，导航并选择您之前创建的 `stock-scanner` 文件夹。
    *   **Compose 文件**: 确保下拉菜单中选择的是 `docker-compose.simple.yml`，或者现在上传。
5.  点击 `下一步`。
6.  向导会显示 Web 门户设置，您可以忽略此步骤，直接点击 `下一步`。(这部也可以跳过)
7.  最后，确认配置无误后，点击 `完成`。
8.  Container Manager 会开始**构建镜像**并启动容器。这个过程因为是第一次构建，**可能需要5-15分钟**，请耐心等待。您可以在日志选项卡中查看构建进度。
9. 如果正常，就可以到下个步骤访问；如果发生端口冲突，则可以回到yml配置文件，修改ports:"8888:8888"中左侧的端口，例如改成`18888`，则后续访问也使用`18888`端口。

### 3: 访问应用
当您看到 `stock-scanner` 项目的状态变为"**运行中**"时，说明部署已成功。

在您的浏览器中，输入以下地址即可访问：
`http://<您的Synology-IP地址>:8888`

## 日常维护

### 如何更新项目latest tag
1.  **Container Manager**: 找到 `stock-scanner` 项目，点击 `操作` -> `停止`。
2.  **Container Manager**: 找到 `Containers` ，选中 `stock-scanner` -> `Action` -> `Delete`，即删除由这个镜像生成的容器。
3.  **Container Manager**: 找到 `Registry`，搜索 `heyfluke/stock-scanner` ，选择`latest` tag，双击更新。
4.  **Container Manager**: 回到 `stock-scanner` 项目，点击 `操作` -> `构建`。

(如果是使用版本号tag，则更新`Project`中`YAML Configuration`中的tag，再重新`Build`即可)。

### 如何查看日志
如果应用无法启动或运行异常，您可以在 Container Manager 中查看日志：
1.  点击 `项目` -> `stock-scanner`。
2.  在下方选择 `容器` 选项卡。
3.  点击名为 `stock-scanner-app` 的容器。
4.  在弹出的窗口中，切换到 `日志` 选项卡，即可看到应用的输出日志，方便排查问题。 