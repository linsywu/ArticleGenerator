/**
 * 文章 API
 */
import { get, post, put, del, patch } from "@/api/client";
import type { Article, PaginatedResponse } from "@/api/types";

export default {
  fetchArticles: (params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }) => get<PaginatedResponse<Article>>("/articles", params as Record<string, unknown>),

  fetchArticle: (id: number) => get<Article>(`/articles/${id}`),

  updateArticleStatus: (id: number, status: string) =>
    patch(`/articles/${id}/status`, { status }),

  updateArticle: (id: number, data: {
    content?: string;
    review_notes?: string;
  }) => put(`/articles/${id}`, data),

  reReviewArticle: (id: number) => post(`/articles/${id}/re-review`),
};
