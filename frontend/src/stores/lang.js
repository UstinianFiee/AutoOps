import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useLangStore = defineStore('lang', () => {
  const lang = ref(localStorage.getItem('lang') || 'zh')
  const isZh = computed(() => lang.value === 'zh')

  function toggle() {
    lang.value = lang.value === 'zh' ? 'en' : 'zh'
    localStorage.setItem('lang', lang.value)
  }

  const dict = {
    // ── 状态 ──────────────────────────────────────────
    success:          ['成功',     'Success'],
    failed:           ['失败',     'Failed'],
    running:          ['执行中',   'Running'],
    pending:          ['等待',     'Pending'],
    online:           ['在线',     'Online'],
    offline:          ['离线',     'Offline'],
    unknown:          ['未知',     'Unknown'],
    stopped:          ['已停止',   'Stopped'],
    deploying:        ['部署中',   'Deploying'],
    // ── 触发方式 ──────────────────────────────────────
    manual:           ['手动',     'Manual'],
    ci:               ['CI自动',   'CI Auto'],
    // ── 任务类型 ──────────────────────────────────────
    init:             ['初始化',   'Init'],
    ping:             ['连通检测', 'Ping'],
    shell:            ['Shell',    'Shell'],
    install:          ['安装包',   'Install'],
    playbook:         ['Playbook', 'Playbook'],
    install_exporter: ['安装监控', 'Install Exporter'],
    // ── 角色 ──────────────────────────────────────────
    admin:            ['管理员',   'Admin'],
    operator:         ['操作员',   'Operator'],
    viewer:           ['只读',     'Viewer'],
    // ── 菜单 ──────────────────────────────────────────
    仪表盘:           ['仪表盘',   'Dashboard'],
    服务器管理:       ['服务器管理','Servers'],
    应用管理:         ['应用管理', 'Apps'],
    容器管理:         ['容器管理', 'Containers'],
    'CI/CD 部署':     ['CI/CD 部署','CI/CD Deploy'],
    监控告警:         ['监控告警', 'Monitor'],
    日志查询:         ['日志查询', 'Logs'],
    'Ansible 任务':   ['Ansible 任务','Ansible Tasks'],
    用户管理:         ['用户管理', 'Users'],
    // ── 导航/顶栏 ─────────────────────────────────────
    收起侧栏:         ['收起侧栏', 'Collapse'],
    退出登录:         ['退出登录', 'Logout'],
    // ── 通用按钮 ──────────────────────────────────────
    刷新:             ['刷新',     'Refresh'],
    保存:             ['保存',     'Save'],
    取消:             ['取消',     'Cancel'],
    删除:             ['删除',     'Delete'],
    编辑:             ['编辑',     'Edit'],
    添加:             ['添加',     'Add'],
    确认:             ['确认',     'Confirm'],
    检测:             ['检测',     'Ping'],
    初始化:           ['初始化',   'Init'],
    安装监控:         ['安装监控', 'Install Monitor'],
  }

  function t(key) {
    if (!key) return key
    const entry = dict[key]
    if (!entry) return key
    return isZh.value ? entry[0] : entry[1]
  }

  return { lang, isZh, toggle, t }
})
