# coding=utf-8
"""
跨区域标题去重模块

在不同展示区域（hotlist, new_items, rss, standalone）之间去除重复标题。
按照 region_order 的顺序，优先保留排在前面的区域中的标题。
"""

import copy
from typing import Dict, List, Optional, Set


def deduplicate_cross_regions(
    report_data: Dict,
    rss_items: Optional[List[Dict]],
    rss_new_items: Optional[List[Dict]],
    standalone_data: Optional[Dict],
    region_order: List[str],
) -> tuple:
    """
    跨区域去重：按照 region_order 顺序，移除后续区域中已出现过的标题

    Args:
        report_data: 报告数据字典，包含 stats（热榜关键词分组）和 new_titles（新增热点）
        rss_items: RSS 关键词统计列表（与 stats 格式一致）
        rss_new_items: RSS 新增统计列表
        standalone_data: 独立展示区数据
        region_order: 区域显示顺序列表

    Returns:
        (report_data, rss_items, rss_new_items, standalone_data) 去重后的数据
    """
    # 深拷贝避免修改原始数据
    report_data = copy.deepcopy(report_data)
    rss_items = copy.deepcopy(rss_items) if rss_items else rss_items
    rss_new_items = copy.deepcopy(rss_new_items) if rss_new_items else rss_new_items
    standalone_data = copy.deepcopy(standalone_data) if standalone_data else standalone_data

    seen_titles: Set[str] = set()

    for region in region_order:
        if region == "ai_analysis":
            continue

        if region == "hotlist":
            _collect_titles_from_stats(report_data.get("stats", []), seen_titles)

        elif region == "new_items":
            _dedup_new_titles(report_data, seen_titles)
            _dedup_stats_list(rss_new_items, seen_titles)

        elif region == "rss":
            _dedup_stats_list(rss_items, seen_titles)

        elif region == "standalone":
            _dedup_standalone(standalone_data, seen_titles)

    # 更新 total_new_count
    if "new_titles" in report_data:
        report_data["total_new_count"] = sum(
            len(source.get("titles", [])) for source in report_data["new_titles"]
        )

    return report_data, rss_items, rss_new_items, standalone_data


def _collect_titles_from_stats(stats: List[Dict], seen: Set[str]) -> None:
    """从 stats 结构中收集标题到 seen 集合（不过滤，只收集）"""
    for stat in stats:
        for title_data in stat.get("titles", []):
            title = title_data.get("title", "")
            if title:
                seen.add(title)


def _dedup_stats_list(stats_list: Optional[List[Dict]], seen: Set[str]) -> None:
    """去重 stats 格式的列表（与热榜 stats 相同结构：[{word, count, titles}]）"""
    if not stats_list:
        return

    for stat in stats_list:
        original_titles = stat.get("titles", [])
        filtered = []
        for td in original_titles:
            title = td.get("title", "")
            if title not in seen:
                filtered.append(td)
                seen.add(title)
        stat["titles"] = filtered
        stat["count"] = len(filtered)

    # 移除没有标题的条目
    stats_list[:] = [s for s in stats_list if s.get("titles")]


def _dedup_new_titles(report_data: Dict, seen: Set[str]) -> None:
    """去重 report_data 中的 new_titles"""
    new_titles = report_data.get("new_titles", [])
    if not new_titles:
        return

    for source_data in new_titles:
        original = source_data.get("titles", [])
        filtered = []
        for td in original:
            title = td.get("title", "")
            if title not in seen:
                filtered.append(td)
                seen.add(title)
        source_data["titles"] = filtered

    # 移除空的 source
    report_data["new_titles"] = [s for s in new_titles if s.get("titles")]


def _dedup_standalone(standalone_data: Optional[Dict], seen: Set[str]) -> None:
    """去重独立展示区数据"""
    if not standalone_data:
        return

    # 去重平台数据
    for platform in standalone_data.get("platforms", []):
        original = platform.get("items", [])
        filtered = []
        for item in original:
            title = item.get("title", "")
            if title not in seen:
                filtered.append(item)
                seen.add(title)
        platform["items"] = filtered

    # 去重 RSS 数据
    for feed in standalone_data.get("rss_feeds", []):
        original = feed.get("items", [])
        filtered = []
        for item in original:
            title = item.get("title", "")
            if title not in seen:
                filtered.append(item)
                seen.add(title)
        feed["items"] = filtered

    # 移除空的
    standalone_data["platforms"] = [p for p in standalone_data.get("platforms", []) if p.get("items")]
    standalone_data["rss_feeds"] = [f for f in standalone_data.get("rss_feeds", []) if f.get("items")]
