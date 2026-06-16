/**
 * 日期时间格式化工具
 *
 * 后端返回的 ISO 8601 字符串（带时区 +00:00 或 Z）会被正确解析，
 * 然后转换为 UTC+8（北京时间）显示。
 */

/**
 * 将 ISO 8601 时间字符串格式化为北京时间显示
 * @param isoStr - ISO 8601 格式的时间字符串，如 "2026-06-16T10:30:00+00:00"
 * @param format - "full" = YYYY-MM-DD HH:mm:ss, "short" = MM-DD HH:mm, "date" = YYYY-MM-DD
 * @returns 格式化后的北京时间字符串，解析失败返回 "-"
 */
export function formatDateTime(
  isoStr: string | null | undefined,
  format: "full" | "short" | "date" = "full"
): string {
  if (!isoStr) return "-";

  try {
    const d = new Date(isoStr);
    // 检查解析是否有效
    if (isNaN(d.getTime())) return "-";

    // 使用 toLocaleString 输出北京时间 (Asia/Shanghai, UTC+8)
    const options: Intl.DateTimeFormatOptions = {
      timeZone: "Asia/Shanghai",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    };

    if (format === "full") {
      options.hour = "2-digit";
      options.minute = "2-digit";
      options.second = "2-digit";
      options.hour12 = false;
    } else if (format === "short") {
      options.hour = "2-digit";
      options.minute = "2-digit";
      options.hour12 = false;
    }

    const formatted = d.toLocaleString("zh-CN", options);

    // toLocaleString("zh-CN") 输出类似 "2026/06/16 14:30:00"
    // 统一转换为 "2026-06-16 14:30:00"
    return formatted.replace(/\//g, "-").replace(/ /g, " ");
  } catch {
    return "-";
  }
}

/**
 * 获取相对时间描述（刚刚 / X分钟前 / X小时前 / X天前）
 * 基于北京时间计算
 */
export function relativeTime(isoStr: string | null | undefined): string {
  if (!isoStr) return "-";

  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return "-";

    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return "刚刚";
    if (diffMin < 60) return `${diffMin}分钟前`;
    if (diffHour < 24) return `${diffHour}小时前`;
    if (diffDay < 30) return `${diffDay}天前`;

    // 超过 30 天显示完整日期
    return formatDateTime(isoStr, "date");
  } catch {
    return "-";
  }
}
