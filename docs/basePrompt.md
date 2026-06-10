#智能数据瞭望与智能问数系统 项目基础信息提示
##1、项目概述
- 本项目是一个基于B/S架构的Web应用程序，采用Tornado web mvc设计实现。
- 目标是构建AI大模型驱动的“智能数据瞭望与智能问数系统”。
- 当前已经具备了一个MVC架构的基础框架能力（login/logout-controllers-models-db）


##2、项目技术栈
- 后端语言：python3.11.9(python -m venv venv建立虚拟空间，在此空间内完成开发)
- web框架：tornado 6.5.6
- 数据库：sqlite3
- 前端技术： html5+css3+js
- 前端UI库与组件：（在项目目标app\static\dist下下载好了zip包，供你本地引用或解压使用）
    - Echarts(未下载，需要后续使用时自行下载本地化部署)
    - fontAwesome(?)
    - bootstrap(?)
    - layui(?)

##3、项目框架设计
- mvc三层经典架构设计
- models:负责数据访问与业务逻辑，当前版本采用sqlite3与数据库交互，通过实体（xxxRepository,如UserRepository）封装数据操作。
- controllers:负责接收Request请求，并处理业务，协调models和view。在tornado中，以RequestHandler的形式存在（xxxHandler，如LoginHandler,logoutHandler）
- view:负责用户界面的呈现和渲染，使用tornado原生模版引擎，结合HTML,css,js渲染页面（如base.html,login.html,admin.html）

##4、目录结构说明
参见 framework.txt文档中的Tree和注释

##5、限制
- 所有开发任务需要基于本基础中的内容完成
- /docs 与开发有关的所有提示/帮助/基础信息全放在该目录，需要在过程中根据任务提示维护和更新
- 与开发有关的所有测试脚本，全放在该目录，不能放在其他目录进行测试