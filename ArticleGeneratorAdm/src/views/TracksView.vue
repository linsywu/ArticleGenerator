<template>
  <div class="tracks-view">
    <PageHeader title="赛道管理" subtitle="管理内容分类体系，配置一级和二级赛道" />

    <div class="toolbar">
      <el-input v-model="searchText" placeholder="搜索赛道..." style="width: 240px" clearable />
      <el-button type="primary" @click="openCreateDialog">+ 新增赛道</el-button>
    </div>

    <el-table :data="filteredTracks" v-loading="loading" style="width: 100%">
      <el-table-column prop="name" label="赛道名称" min-width="140">
        <template #default="{ row }">
          <span style="font-weight: 600;">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
            {{ row.status === 1 ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="openEditDialog(row)">编辑</el-button>
          <el-button size="small" text @click="toggleStatus(row)">
            {{ row.status === 1 ? '停用' : '启用' }}
          </el-button>
          <el-popconfirm title="删除赛道将同时删除所有二级赛道，确认？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button size="small" text type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="sub-track-section">
            <div class="sub-track-header">
              <strong>二级赛道</strong>
              <el-button size="small" type="primary" @click="openSubTrackDialog(row)">+ 添加</el-button>
            </div>
            <div v-if="!row.sub_tracks?.length" style="color: #999; padding: 12px 0;">暂无二级赛道</div>
            <div v-for="sub in row.sub_tracks" :key="sub.id" class="sub-track-row">
              <span>{{ sub.name }}</span>
              <span v-if="sub.description" style="color: #999; margin-left: 8px;">— {{ sub.description }}</span>
              <span style="flex: 1;"></span>
              <el-button size="small" text @click="openSubTrackEdit(sub)">编辑</el-button>
              <el-popconfirm title="确认删除？" @confirm="handleDeleteSub(sub.id)">
                <template #reference>
                  <el-button size="small" text type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- Track Dialog -->
    <el-dialog v-model="dialogVisible" :title="editingTrack ? '编辑赛道' : '新增赛道'" width="500px">
      <el-form :model="form" label-position="top">
        <el-form-item label="赛道名称" required>
          <el-input v-model="form.name" placeholder="如：AI科技" />
        </el-form-item>
        <el-form-item label="赛道描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="赛道简介..." />
        </el-form-item>
        <el-form-item label="热门关键词 (JSON数组)">
          <el-input v-model="form.keywords" placeholder='["AI", "ChatGPT"]' />
        </el-form-item>
        <el-form-item label="禁用关键词 (JSON数组)">
          <el-input v-model="form.forbidden_keywords" placeholder='["赌博", "色情"]' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- SubTrack Dialog -->
    <el-dialog v-model="subDialogVisible" title="二级赛道" width="400px">
      <el-form :model="subForm" label-position="top">
        <el-form-item label="名称" required>
          <el-input v-model="subForm.name" placeholder="如：大模型" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="subForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="subDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage } from "element-plus";
import tracksApi from "@/api/modules/tracks";
import type { Track, SubTrack } from "@/api/types";
import PageHeader from "@/components/PageHeader.vue";

const tracks = ref<Track[]>([]);
const loading = ref(false);
const searchText = ref("");

const filteredTracks = computed(() => {
  if (!searchText.value) return tracks.value;
  const q = searchText.value.toLowerCase();
  return tracks.value.filter(t => t.name.toLowerCase().includes(q));
});

const dialogVisible = ref(false);
const editingTrack = ref<Track | null>(null);
const form = ref({ name: "", description: "", keywords: "", forbidden_keywords: "" });

function openCreateDialog() {
  editingTrack.value = null;
  form.value = { name: "", description: "", keywords: "", forbidden_keywords: "" };
  dialogVisible.value = true;
}

function openEditDialog(row: Track) {
  editingTrack.value = row;
  form.value = {
    name: row.name,
    description: row.description || "",
    keywords: row.keywords || "",
    forbidden_keywords: row.forbidden_keywords || "",
  };
  dialogVisible.value = true;
}

async function handleSave() {
  if (!form.value.name.trim()) { ElMessage.warning("请输入赛道名称"); return; }
  try {
    if (editingTrack.value) {
      await tracksApi.updateTrack(editingTrack.value.id, form.value);
      ElMessage.success("赛道已更新");
    } else {
      await tracksApi.createTrack(form.value);
      ElMessage.success("赛道已创建");
    }
    dialogVisible.value = false;
    await fetchTracks();
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || "操作失败"); }
}

async function toggleStatus(row: Track) {
  const newStatus = row.status === 1 ? 0 : 1;
  await tracksApi.toggleTrackStatus(row.id, newStatus);
  row.status = newStatus;
  ElMessage.success(newStatus === 1 ? "已启用" : "已停用");
}

async function handleDelete(id: number) {
  await tracksApi.deleteTrack(id);
  ElMessage.success("赛道已删除");
  await fetchTracks();
}

const subDialogVisible = ref(false);
const editingSubTrack = ref<SubTrack | null>(null);
const currentTrack = ref<Track | null>(null);
const subForm = ref({ name: "", description: "" });

function openSubTrackDialog(track: Track) {
  currentTrack.value = track;
  editingSubTrack.value = null;
  subForm.value = { name: "", description: "" };
  subDialogVisible.value = true;
}

function openSubTrackEdit(sub: SubTrack) {
  editingSubTrack.value = sub;
  subForm.value = { name: sub.name, description: sub.description || "" };
  subDialogVisible.value = true;
}

async function handleSubSave() {
  if (!subForm.value.name.trim()) { ElMessage.warning("请输入二级赛道名称"); return; }
  try {
    if (editingSubTrack.value) {
      await tracksApi.updateSubTrack(editingSubTrack.value.id, subForm.value);
    } else if (currentTrack.value) {
      await tracksApi.createSubTrack(currentTrack.value.id, subForm.value);
    }
    ElMessage.success("保存成功");
    subDialogVisible.value = false;
    await fetchTracks();
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || "操作失败"); }
}

async function handleDeleteSub(subId: number) {
  await tracksApi.deleteSubTrack(subId);
  ElMessage.success("二级赛道已删除");
  await fetchTracks();
}

async function fetchTracks() {
  loading.value = true;
  try { const { data } = await tracksApi.fetchTracks(); tracks.value = data as any; }
  finally { loading.value = false; }
}

onMounted(fetchTracks);
</script>

<style scoped>
.tracks-view { max-width: 960px; margin: 0 auto; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.sub-track-section { padding: 8px 24px 16px; }
.sub-track-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.sub-track-row { display: flex; align-items: center; padding: 6px 0; border-bottom: 1px solid #f0f0f0; }
</style>
