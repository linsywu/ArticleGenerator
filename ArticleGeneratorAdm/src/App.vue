<template>
  <el-container class="layout">
    <el-aside width="200px" class="aside">
      <div class="logo">ArticleGenerator</div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/">热点列表</el-menu-item>
        <el-menu-item index="/generate">文章生成</el-menu-item>
        <el-menu-item index="/tasks">任务列表</el-menu-item>
        <el-menu-item index="/review">文章评审</el-menu-item>
        <el-menu-item index="/publish">待发布</el-menu-item>
        <el-menu-item index="/hotspot-sources">热点源管理</el-menu-item>
        <el-menu-item index="/distill">风格蒸馏</el-menu-item>
        <el-menu-item index="/accounts">账号管理</el-menu-item>
        <el-menu-item index="/providers">API 供应商</el-menu-item>
        <el-menu-item index="/scenario-configs">场景配置</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
</script>

<style>
*{
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
.layout {
  height: 100vh;
}
.aside {
  background: #304156;
}
.logo {
  height: 50px;
  line-height: 50px;
  text-align: center;
  color: #fff;
  font-weight: bold;
}
.main {
  background: #f0f2f5;
  padding: 20px;
}
</style>
