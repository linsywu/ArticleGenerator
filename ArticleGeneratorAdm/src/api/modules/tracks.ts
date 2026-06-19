/**
 * 赛道 API
 */
import { get, post, put, del, patch } from "@/api/client";
import type { Track, SubTrack } from "@/api/types";

export default {
  fetchTracks: () => get<Track[]>("/tracks"),

  createTrack: (data: {
    name: string;
    description?: string;
    keywords?: string;
    forbidden_keywords?: string;
  }) => post<Track>("/tracks", data),

  getTrack: (id: number) => get<Track>(`/tracks/${id}`),

  updateTrack: (id: number, data: {
    name?: string;
    description?: string;
    keywords?: string;
    forbidden_keywords?: string;
  }) => put<Track>(`/tracks/${id}`, data),

  toggleTrackStatus: (id: number, status: number) =>
    patch(`/tracks/${id}/status`, { status }),

  deleteTrack: (id: number) => del(`/tracks/${id}`),

  createSubTrack: (trackId: number, data: { name: string; description?: string }) =>
    post<SubTrack>(`/tracks/${trackId}/sub-tracks`, data),

  updateSubTrack: (id: number, data: { name: string; description?: string }) =>
    put<SubTrack>(`/tracks/sub-tracks/${id}`, data),

  deleteSubTrack: (id: number) => del(`/tracks/sub-tracks/${id}`),
};
