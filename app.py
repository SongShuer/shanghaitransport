# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import streamlit as st
import requests
import os

# 读取高德 Key
try:
    GAODE_KEY = st.secrets["GAODE_KEY"]
except (KeyError, AttributeError):
    # 本地开发时可用环境变量（或直接设为空用于测试）
    GAODE_KEY = os.getenv("GAODE_KEY", "")

if not GAODE_KEY:
    st.error("高德地图 API Key 未配置！请在 Streamlit Cloud 的 Secrets 中设置。")
    st.stop()

def geocode(address):
    """地址转坐标"""
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {"address": address, "key": GAODE_KEY, "city": "上海"}
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if data.get("status") == "1" and data.get("geocodes"):
            return data["geocodes"][0]["location"]
    except:
        pass
    return None

def get_transit_route(origin, dest):
    """获取公交路线"""
    url = "https://restapi.amap.com/v5/direction/transit/integrated"
    params = {
        "key": GAODE_KEY,
        "origin": origin,
        "destination": dest,
        "city1": "310000",
        "city2": "310000",
        "strategy": "2",
        "extensions": "all"
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if data.get("status") == "1":
            return data.get("route", {}).get("transits", [])
    except:
        pass
    return []

def parse_route_v5(transit):

    lines = []
    total_distance = 0

    for seg in transit.get("segments", []):
        # 处理 buslines
        bus = seg.get("bus", {})
        if isinstance(bus, dict):
            for line in bus.get("buslines", []):
                name = line.get("name", "")
                # 提取 "X号线"
                if "地铁" in name and "号线" in name:
                    start = name.find("地铁") + 2
                    end = name.find("号线") + 2
                    if start < end:
                        line_name = name[start:end]
                        if line_name not in lines:
                            lines.append(line_name)
                # 累加距离
                dist = line.get("distance")
                if dist and dist.isdigit():
                    total_distance += int(dist)
        
        # 累加步行距离
        walking = seg.get("walking", {})
        walk_dist = walking.get("distance")
        if walk_dist and walk_dist.isdigit():
            total_distance += int(walk_dist)

    # 估算时间（400米/分钟）
    estimated_time = max(1, total_distance // 400)
    return lines, estimated_time, total_distance / 1000

# ==============================
# Streamlit 界面
# ==============================
st.set_page_config(page_title="🚇 上海地铁助手", layout="centered")
st.title("🚇 上海地铁助手")
st.caption("输入起点和终点（建议加'地铁站'）")

col1, col2 = st.columns(2)
with col1:
    start = st.text_input("起点", "场中路地铁站")
with col2:
    end = st.text_input("终点", "徐家汇地铁站")

if st.button("规划路线"):
    with st.spinner("查询中..."):
        # 1. 地理编码
        origin_loc = geocode(start)
        dest_loc = geocode(end)
        if not origin_loc or not dest_loc:
            st.error("❌ 地址无法解析，请检查输入（建议加'地铁站'）")
            st.stop()

        # 2. 查询路线
        routes = get_transit_route(origin_loc, dest_loc)
        if not routes:
            st.error("❌ 未找到路线")
            st.stop()

        # 3. 解析第一条路线
        lines, time_min, distance_km = parse_route_v5(routes[0])

        # 4. 显示结果
        st.success("✅ 规划成功！")
        st.write(f"预计耗时：**{time_min} 分钟**")
        st.write(f"总距离：**{distance_km:.1f} 公里**")
        if lines:
            st.write(f"途经线路：{' → '.join(lines)}")
        else:
            st.write("未识别到地铁线路")
