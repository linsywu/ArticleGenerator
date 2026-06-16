<template>
  <div class="page">
    <div class="toolbar">
      <el-button type="primary" @click="openAdd">新增热点源</el-button>
    </div>

    <el-empty v-if="!loading && list.length === 0" description="暂无热点源配置">
      <template #description>
        <p>热点源用于配置抓取来源，抓取模块会读取启用的热点源</p>
        <el-button type="primary" @click="openAdd">新增热点源</el-button>
      </template>
    </el-empty>
    <el-table v-else :data="list" v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="名称" width="120" />
      <el-table-column prop="type" label="类型/标识" width="120" />
      <el-table-column prop="config" label="配置" min-width="150" show-overflow-tooltip />
      <el-table-column prop="enabled" label="启用" width="80">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? "是" : "否" }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑热点源' : '新增热点源'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="如：微博热搜" />
        </el-form-item>
        <el-form-item label="类型/标识">
          <el-select v-model="form.type" placeholder="选择或输入" filterable allow-create style="width: 100%">
            <el-option label="weibo" value="weibo" />
            <el-option label="zhihu" value="zhihu" />
            <el-option label="baidu" value="baidu" />
            <el-option label="douyin" value="douyin" />
            <el-option label="bilihot" value="bilihot" />
          </el-select>
        </el-form-item>
        <el-form-item label="配置">
          <el-input v-model="form.config" type="textarea" rows="2" placeholder="可选，JSON 格式" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doSave">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api, type HotspotSource } from "@/api/client";
import { formatDateTime } from "@/utils/format";

const list = ref<HotspotSource[]>([]);
const loading = ref(false);
const dialogVisible = ref(false);
const saving = ref(false);
const editingId = ref<number | null>(null);
const form = reactive({ name: "", type: "weibo", config: "", enabled: true });

async function load() {
  loading.value = true;
  try {
    const res = await api.getHotspotSourceList();
    list.value = res.data || [];
  } catch (e) {
    ElMessage.error("加载失败");
  } finally {
    loading.value = false;
  }
}

function openAdd() {
  editingId.value = null;
  form.name = "";
  form.type = "weibo";
  form.config = "";
  form.enabled = true;
  dialogVisible.value = true;
}

function openEdit(row: HotspotSource) {
  editingId.value = row.id;
  form.name = row.name;
  form.type = row.type;
  form.config = row.config || "";
  form.enabled = row.enabled;
  dialogVisible.value = true;
}

async function doSave() {
  if (!form.name || !form.type) {
    ElMessage.warning("请填写名称和类型");
    return;
  }
  saving.value = true;
  try {
    if (editingId.value) {
      await api.updateHotspotSource(editingId.value, form);
      ElMessage.success("更新成功");
    } else {
      await api.createHotspotSource(form);
      ElMessage.success("添加成功");
    }
    dialogVisible.value = false;
    load();
  } catch (e) {
    ElMessage.error(editingId.value ? "更新失败" : "添加失败");
  } finally {
    saving.value = false;
  }
}

async function del(row: HotspotSource) {
  try {
    await ElMessageBox.confirm(`确定删除热点源「${row.name}」？`, "提示");
    await api.deleteHotspotSource(row.id);
    ElMessage.success("删除成功");
    load();
  } catch (e) {
    if (e !== "cancel") ElMessage.error("删除失败");
  }
}

onMounted(load);
</script>

<style scoped>
.page {
  background: transparent;
  padding: 20px;
  border-radius: 4px;
}
.toolbar {
  margin-bottom: 16px;
}
</style>
