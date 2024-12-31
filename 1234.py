import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 设置页面配置
st.set_page_config(
    page_title="销量与补货洞察",
    layout="wide",
)

@st.cache_data
def load_data(path):
    # 读取CSV文件
    try:
        df = pd.read_csv(path)
    except Exception as e:
        st.error(f"读取CSV文件时出错: {e}")
        return pd.DataFrame()
    
    # 打印原始列名以检查
    st.write("原始 DataFrame 列名:", df.columns.tolist())
    
    # 统一列名格式：去除空格并转换为小写
    df.columns = df.columns.str.strip().str.lower()
    
    # 打印标准化后的列名
    st.write("标准化后的 DataFrame 列名:", df.columns.tolist())
    
    # 定义所需的列（全小写）
    required_columns = ['title', 'variation', 'id', 'type', 'country', 'channel']
    
    # 检查缺失的列
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"以下必需的列在数据中缺失: {missing_columns}")
        return pd.DataFrame()  # 或者采取其他适当的处理方式
    
    # 删除关键字段中的NaN值
    df = df.dropna(subset=required_columns)
    
    # 分离销售和补货列
    sales_cols = [col for col in df.columns if '_sales' in col]
    restocks_cols = [col for col in df.columns if '_restocks' in col]
    
    # 检查销售和补货列是否存在
    if not sales_cols:
        st.error("没有找到包含 '_sales' 的列。")
        return pd.DataFrame()
    if not restocks_cols:
        st.error("没有找到包含 '_restocks' 的列。")
        return pd.DataFrame()
    
    # 转换销售数据
    sales_df = df.melt(id_vars=required_columns,
                       value_vars=sales_cols,
                       var_name='date',
                       value_name='sales')
    sales_df['date'] = sales_df['date'].str.replace('_sales', '')
    sales_df['date'] = pd.to_datetime(sales_df['date'], errors='coerce')
    sales_df = sales_df.dropna(subset=['date'])
    
    # 转换补货数据
    restocks_df = df.melt(id_vars=required_columns,
                          value_vars=restocks_cols,
                          var_name='date',
                          value_name='restocks')
    restocks_df['date'] = restocks_df['date'].str.replace('_restocks', '')
    restocks_df['date'] = pd.to_datetime(restocks_df['date'], errors='coerce')
    restocks_df = restocks_df.dropna(subset=['date'])
    
    # 合并销售和补货数据
    merged_df = pd.merge(sales_df, restocks_df, on=required_columns + ['date'], how='outer')
    
    # 填充NaN值为0
    merged_df['sales'] = merged_df['sales'].fillna(0)
    merged_df['restocks'] = merged_df['restocks'].fillna(0)
    
    return merged_df

# 数据路径（请确保路径指向新的 CSV 文件）
data_path = r'E:\carlos\市场调研\carlos\销量洞察\交互图\20241231\工作簿1.csv'

# 加载数据
merged_df = load_data(data_path)

# 如果数据加载失败，停止执行
if merged_df.empty:
    st.stop()

# 定义可筛选的字段（全小写）
filter_fields = ['title', 'variation', 'type', 'country', 'channel']

# 初始化Session State for filters
if 'filters' not in st.session_state:
    st.session_state.filters = {field: [] for field in filter_fields}

# 定义全选和全不选功能
def select_all(field, options):
    st.session_state.filters[field] = list(options)

def deselect_all(field):
    st.session_state.filters[field] = []

# 获取当前筛选条件
def get_filtered_df():
    df = merged_df.copy()
    for field in filter_fields:
        if st.session_state.filters[field]:
            df = df[df[field].isin(st.session_state.filters[field])]
    return df

# 动态获取每个筛选器的可选项
def get_filter_options(df, field):
    return sorted(df[field].unique())

# 设置侧边栏
st.sidebar.header("筛选条件")

# 获取初始筛选条件
filtered_df_initial = get_filtered_df()

# 动态更新筛选器选项
for field in filter_fields:
    temp_df = merged_df.copy()
    # 应用其他筛选器的条件
    for other_field in filter_fields:
        if other_field != field and st.session_state.filters[other_field]:
            temp_df = temp_df[temp_df[other_field].isin(st.session_state.filters[other_field])]
    # 获取当前字段的可选项
    options = get_filter_options(temp_df, field)
    
    # 确保当前选择在可选项中
    current_selection = st.session_state.filters[field]
    current_selection = [item for item in current_selection if item in options]
    st.session_state.filters[field] = current_selection
    
    # 创建过滤器
    st.sidebar.subheader(field.capitalize())
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.sidebar.button("全选", key=f"select_all_{field}", on_click=select_all, args=(field, options))
    with col2:
        st.sidebar.button("全不选", key=f"deselect_all_{field}", on_click=deselect_all, args=(field,))
    
    selected = st.sidebar.multiselect(
        f"选择 {field.capitalize()}",
        options=options,
        default=st.session_state.filters[field],
        key=f"{field}_multiselect"
    )
    st.session_state.filters[field] = selected

# 日期选择
st.sidebar.subheader("日期范围选择")
min_date = merged_df['date'].min()
max_date = merged_df['date'].max()
start_date, end_date = st.sidebar.date_input("选择日期范围", [min_date, max_date], min_value=min_date, max_value=max_date)

# 时间间隔选择
st.sidebar.subheader("时间间隔")
interval = st.sidebar.selectbox("选择时间间隔", options=['7 天', '15 天', '30 天'], index=0)
interval_days = int(interval.split()[0])

# 过滤数据
filtered_df = get_filtered_df()
filtered_df = filtered_df[
    (filtered_df['date'] >= pd.to_datetime(start_date)) &
    (filtered_df['date'] <= pd.to_datetime(end_date))
]

# 如果过滤后没有数据，提示用户
if filtered_df.empty:
    st.warning("没有匹配的数据，请调整筛选条件。")
else:
    # 聚合销售数据
    sales_agg = filtered_df.groupby(['title', pd.Grouper(key='date', freq=f'{interval_days}D')])['sales'].sum().reset_index()
    sales_agg = sales_agg.sort_values('date')
    
    # 聚合补货数据（转换为绝对值）
    restocks_agg = filtered_df.groupby(['title', pd.Grouper(key='date', freq=f'{interval_days}D')])['restocks'].sum().reset_index()
    restocks_agg['restocks'] = restocks_agg['restocks'].abs()
    restocks_agg = restocks_agg.sort_values('date')
    
    # 绘制销售趋势图
    st.subheader("销售趋势")
    fig_sales = px.line(sales_agg, x='date', y='sales', color='title',
                        labels={'date': '日期', 'sales': '销售量', 'title': '标题'},
                        title='销售趋势图')
    st.plotly_chart(fig_sales, use_container_width=True)
    
    # 绘制补货趋势图
    st.subheader("补货趋势")
    fig_restocks = px.line(restocks_agg, x='date', y='restocks', color='title',
                           labels={'date': '日期', 'restocks': '补货量', 'title': '标题'},
                           title='补货趋势图')
    st.plotly_chart(fig_restocks, use_container_width=True)
    
    # 显示过滤后的数据表
    st.subheader("过滤后的数据")
    st.dataframe(filtered_df)

