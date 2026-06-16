/**
 * 热点 API
 */
import { get, post, put, del } from "@/api/client";
import type {
  Hotspot,
  PaginatedResponse,
  HotspotSource,
} from "@/api/types";

export default {
  fetchHotspots: (params?: {
    status?: string;
    source?: string;
    keyword?: string;
    page?: number;
    page_size?: number;
  }) => get<PaginatedResponse<Hotspot>>("/hotspots", params as Record<string, unknown>),

  fetchHotspotSourceOptions: () => get<{ sources: string[] }>("/hotspots/sources"),

  crawlHotspots: () => post<{ created: number; total: number; error?: string }>("/hotspots/crawl"),

  fetchHotspotSources: () => get<HotspotSource[]>("/hotspot-sources"),

  createHotspotSource: (data: {
    name: string;
    type: string;
    config?: string;
    enabled?: boolean;
  }) => post<HotspotSource>("/hotspot-sources", data),

  updateHotspotSource: (id: number, data: {
    name?: string;
    type?: string;
    config?: string;
    enabled?: boolean;
  }) => put<HotspotSource>(`/hotspot-sources/${id}`, data),

  deleteHotspotSource: (id: number) => del(`/hotspot-sources/${id}`),
};
