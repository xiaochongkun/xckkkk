# 安全指南

## 🔒 API密钥安全

### ⚠️ 重要提醒
- **绝不要**将真实API密钥提交到版本控制系统
- **绝不要**在代码中硬编码API密钥  
- **绝不要**在公开场所分享包含密钥的配置文件

### ✅ 正确做法

1. **使用环境变量**
   ```bash
   # 复制模板文件
   cp .env.example .env
   
   # 编辑并填入真实密钥
   nano .env
   ```

2. **验证.gitignore配置**
   ```bash
   # 确保.env文件被忽略
   grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore
   ```

3. **在生产环境中使用密钥管理服务**
   - AWS Secrets Manager
   - Azure Key Vault  
   - Google Secret Manager
   - HashiCorp Vault

## 🛡️ 模型版本安全

### 当前使用模型
- **Claude 3.5 Sonnet (20241022)** - 最新稳定版本

### 避免使用废弃模型
- ❌ `claude-3-5-sonnet-20240620` (将于2025年10月22日停用)

## 🔐 外部服务安全

### MCP服务器连接
项目连接以下外部MCP服务器：
- 写操作服务器: `http://103.149.46.64:8000/protocol/mcp/`
- 读操作服务器: `https://twitter-mcp.gc.rrrr.run/sse`

### 安全措施
- ✅ 连接超时保护 (20秒)
- ✅ 工具执行超时 (30秒)
- ✅ 断路器模式防雪崩
- ✅ 错误处理和降级机制

## 🚨 安全事件响应

### 如果API密钥泄露
1. **立即轮换密钥**
   - Anthropic控制台: https://console.anthropic.com/
   - Tavily控制台: https://app.tavily.com/

2. **检查访问日志**
   - 查看是否有异常API调用
   - 监控账单变化

3. **更新所有部署环境**
   - 开发环境
   - 测试环境  
   - 生产环境

### 报告安全问题
如发现安全漏洞，请：
1. 不要在公开issue中讨论
2. 发送邮件至项目维护者
3. 提供详细的漏洞描述和复现步骤

## 📋 安全检查清单

### 部署前检查
- [ ] API密钥已从代码中移除
- [ ] .env文件已正确配置  
- [ ] .gitignore包含.env文件
- [ ] 使用最新稳定的模型版本
- [ ] 外部服务连接已配置超时
- [ ] 错误处理机制已测试

### 定期检查
- [ ] 检查依赖项安全更新
- [ ] 审查API密钥访问权限
- [ ] 监控异常API调用
- [ ] 验证备份和恢复流程

## 🔗 相关资源

- [Anthropic安全最佳实践](https://docs.anthropic.com/claude/docs/security)
- [Python应用安全指南](https://cheatsheetseries.owasp.org/cheatsheets/Python_Security_Cheat_Sheet.html)
- [API密钥管理最佳实践](https://owasp.org/www-community/vulnerabilities/Insecure_Storage_of_Sensitive_Information)