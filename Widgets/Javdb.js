var WidgetMetadata = {
    id: "javdb_search_enhanced",
    title: "JavDB",
    description: "获取 JavDB 搜索",
    author: "",
    site: "https://javdb.com",
    version: "1.0.0",
    requiredVersion: "0.0.1",
    modules: [
        {
            title: "JavDB 搜索",
            description: "输入关键词•番号搜索影片",
            requiresWebView: false,
            functionName: "searchJavDB",
            sectionMode: false,
            cacheDuration: 300,
            params: [
                {
                    name: "code",
                    title: "关键词•番号",
                    type: "input",
                    description: "输入番号或者关键词(如:DLDSS-408或者楪カレン)",
                    value: "",
                    placeholders: [
                        { 
              title: "示例番号", value: "DLDSS-408" 
            },
            { 
              title: "示例关键词", value: "楪カレン" 
                        }
                    ]
                }
            ]
        }
    ]
};

async function searchJavDB(params = {}) {
    try {
        if (!params.code?.trim()) {
            throw new Error("请输入有效的番号（如DLDSS-408）");
        }
        const code = params.code.trim().toUpperCase();
        const searchUrl = `https://javdb.com/search?q=${encodeURIComponent(code)}&f=all`;
        console.log("正在请求搜索页面：", searchUrl);
        const searchRes = await Widget.http.get(searchUrl, {
            headers: {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9"
            }
        });
        console.log("搜索请求状态码：", searchRes.statusCode);
        const html = searchRes.data?.toString() || "";
        if (!html) throw new Error("搜索页面返回空内容");
        const $ = Widget.html.load(html);
        if (!$) throw new Error("HTML解析失败：页面内容格式错误");
        const $list = $(".movie-list");
        if ($list.length === 0) throw new Error("未找到搜索结果：可能番号错误或页面结构变化");
        const movies = [];
        for (const item of $list.find(".item").toArray()) {
            const $item = $(item);
            const itemUrl = $item.find("a").attr("href");
            if (!itemUrl) continue;
            try {
                const detailData = await getMovieDetailWithVideo(`https://javdb.com${itemUrl}`);
                const titleWithDuration = `${$item.find(".video-title").text()?.trim() || "未知标题"} - ${detailData.duration}`;
                
                movies.push({
                    id: itemUrl,
                    type: "url",
                    title: titleWithDuration,
                    backdropPath: $item.find(".cover img").attr("src") || "",
                    previewUrl: detailData.previewVideo || "",
                    link: `https://javdb.com${itemUrl}`,
                    mediaType: "movie",
                    durationText: detailData.duration || "00:00",
                    description: detailData.description,
                    videoUrl: detailData.videoUrl || ""
                });
            } catch (itemError) {
                console.warn(`单个电影解析失败（${itemUrl}）:`, itemError.message);
                continue;
            }
        }
        return movies;
    } catch (error) {
        console.error("已被风控，请更换ip地址后重试：", error.stack);
        throw new Error(`搜索失败：${error.message}`);
    }
}

async function getMovieDetailWithVideo(detailUrl) {
    try {
        const detailRes = await Widget.http.get(detailUrl, {
            headers: {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9"
            }
        });
        const detailHtml = detailRes.data?.toString() || "";
        if (!detailHtml) throw new Error("详情页返回空内容");
        const $detail = Widget.html.load(detailHtml);
        if (!$detail) throw new Error("详情页HTML解析失败");
        let videoUrl = "";
        const videoIframe = $detail("#video-container iframe");
        if (videoIframe.length > 0) {
            videoUrl = videoIframe.attr("src") || "";
        }
        if (!videoUrl) {
            const videoApiLink = $detail('a[href*="/video/"]').attr("href");
            if (videoApiLink) {
                const apiRes = await Widget.http.get(`https://javdb.com${videoApiLink}`, {
                    headers: { "Referer": detailUrl }
                });
                const apiData = JSON.parse(apiRes.data || "{}");
                videoUrl = apiData.url || "";
            }
        }
        if (!videoUrl) {
            const descLinks = $detail(".movie-info a").toArray();
            for (const link of descLinks) {
                const href = $(link).attr("href") || "";
                if (href.includes("streaming") || href.includes("play")) {
                    videoUrl = href;
                    break;
                }
            }
        }
        let previewVideo = $detail("#preview-video source").attr("src") || $detail(".magnet-name > a").first().attr("href");
        if (previewVideo) {
            if (previewVideo.startsWith('//')) {
                previewVideo = `https:${previewVideo}`;
            }
            else if (!previewVideo.startsWith('http://') && !previewVideo.startsWith('https://')) {
                const baseUrl = 'https://javdb.com';
                previewVideo = new URL(previewVideo, baseUrl).href;
            }
            else if (previewVideo.startsWith('http://')) {
                previewVideo = previewVideo.replace('http://', 'https://');
            }
        }
        const durationElement = $detail(".panel-block strong:contains('時長')").parent().find('.value');
        const duration = durationElement.text()?.trim() || $detail(".score").prev().text()?.trim() || "00:00";
        
        const descElement = $detail(".panel-block strong:contains('簡介')").parent().find('.value');
        const description = descElement.text()?.trim() || $detail(".movie-info").text()?.trim();

        return {
            videoUrl: videoUrl.trim(),
            duration: duration.trim(),
            previewVideo: previewVideo.trim(),
            description: description.trim()
        };
    } catch (error) {
        console.warn(`获取播放地址失败（${detailUrl}）:`, error.message);
        return {
            videoUrl: "",
            duration: "00:00",
            previewVideo: "",
            description: ""
        };
    }
}
