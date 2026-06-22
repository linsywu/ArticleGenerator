/**
 * 素材中心 API
 */
import { get, post } from "@/api/client";
import type { MpMaterial } from "@/api/types";

export default {
  fetchMaterials: (params?: { account_id?: number; search?: string; page?: number; page_size?: number }) =>
    get<{ data: MpMaterial[]; total: number }>("/materials", params),

  getMaterial: (id: number) => get<any>(`/materials/${id}`),

  parseMaterial: (id: number) => post<{ content_markdown: string; cached: boolean }>(`/materials/${id}/parse`),

  generateSummary: (materialId: number, title: string, content: string) =>
    post<{ task_id: string; status: string; message: string }>(
      `/materials/${materialId}/generate-summary`,
      { title, content }
    ),
};
