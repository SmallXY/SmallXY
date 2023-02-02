# ← 我就是傻逼OK~ 下面代码 求评价 我就不该活着谢谢 我愿意的东西没有人支持 水人不配活着确实 来不及加红色字体= = 我就是格废物 插件解说录不出来 我TM也想活着 不管怎样最亲近的人疯狂说我我没法表达 我想哭但是没法表达我 我好不容易觉得MC插件很好玩 现在被说的没有信念了 没有信念我了活着真的没必要 我受不了我所有的事情.....我天生不知好赖，比如一顿饭有剩菜有新做的 我会非常喜欢吃剩菜


```java
/*
 *
 *  * Copyright (c) 2022. 最终解释权 制作者： 小玄易(葛宝檀)
 *
 */

package net.lanternstudio.toolsapi.FileManager;


import net.lanternstudio.toolsapi.Console.CMessage;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class DownloadFile {

    /**
     *
     * @param DownLoadUrl 下载链接
     * @param FilePath 带着文件名字的
     * @param FileNameNoSuffix 没有后缀的文件名字
     * @throws Exception
     */
    public void start(String DownLoadUrl, File FilePath, String FileNameNoSuffix) throws Exception {
        //判断文件是否存在，不存在则创建文件
        CMessage.send("§a " + FileNameNoSuffix + "需要同步");
        if (!FilePath.exists()) {
            if (FilePath.getParentFile().mkdir()) {
                CMessage.send("§a " + FilePath.getParentFile() + "文件夹不在创建完毕");
            }
            if (FilePath.createNewFile()) {
                CMessage.send("§a 创建" + FileNameNoSuffix + "文件");
            }
        }
        URL url = new URL(DownLoadUrl);
        //使用http打开这个URL 以及设置连接的时间与超时时间
        HttpURLConnection urlCon = (HttpURLConnection) url.openConnection();
        urlCon.setConnectTimeout(6000);
        urlCon.setReadTimeout(6000);
        int code = urlCon.getResponseCode();
        if (code != HttpURLConnection.HTTP_OK)
            throw new Exception("[Lantern] 文件读取失败 检查阿里云桶子");
        DataInputStream in = new DataInputStream(urlCon.getInputStream());
        DataOutputStream out = new DataOutputStream(new FileOutputStream(FilePath));
        byte[] buffer = new byte[2048];
        int count = 0;
        while ((count = in.read(buffer)) > 0) {
            out.write(buffer, 0, count);
        }
        CMessage.send("§a " + FileNameNoSuffix + "同步完成");
        try {
            out.close();
            in.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

}
```

![banner](https://github.com/SmallXY/SmallXY/blob/main/githubbanner.png)

![qwq](https://img.shields.io/badge/QwQ-1-informational) 
[![qwq](https://img.shields.io/badge/直播间-2-ff69b4)](https://live.bilibili.com/2211693) 
[![qwq](https://img.shields.io/badge/kook交流-3-green)](https://kook.top/G1tIlv) 
[![qwq](https://img.shields.io/badge/QQ频道粉丝-搜索玄易的超大窝-orange)]()
