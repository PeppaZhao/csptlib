"""
用于绘制轨迹图、普渡图

Author: CheneyZhao.wust.edu
        cheneyzhao@126.com
"""
import bisect
import copy
import itertools

import matplotlib
from typing import Any
from datastore import save_variable
import matplotlib.pyplot as transplt
import numpy as np
import math
from datastore import AterialDataCollection

# 设置显示中文字体
matplotlib.rc("font", family='SimSun')


class SignalPlanPlot(AterialDataCollection):
    """
    绘制配时方案及车辆轨迹
    """

    def __init__(self,
                 LoadNet_name: str = None, LoadLayout_name: str = None,
                 link_num_inbound: list = None, link_num_outbound: list = None,
                 phase_inbound: list = None, phase_outbound: list = None,
                 SignalHeads_num_inbound: list = None, SignalHeads_num_outbound: list = None,
                 SignalHeads_num_inboundL: list = None, SignalHeads_num_outboundL: list = None, /,
                 gw_speed: float = None, period: int = 3600):
        """
        用于绘制当前干线系统配时方案，两种途径：
        （1）load Vis-sim File data
        实例化输入参数
        :param period: 仿真周期，默认3600s -> int
        :param gw_speed: 设置绿波速度 -> float
        :param LoadNet_name: Vis-sim inp文件位置 -> str
        :param LoadLayout_name: Vis-sim in0文件位置 -> str
        :param link_num_inbound: inbound干线路段编号 -> list[int]
        :param link_num_outbound: outbound干线路段编号 -> list[int]
        :param phase_inbound: outbound干线路段编号 -> list[int]
        :param phase_outbound: outbound干线路段编号 -> list[int]
        :param SignalHeads_num_inbound: inbound干线直行灯头编号 -> list[list[int]]
        :param SignalHeads_num_outbound: outbound干线直行灯头编号 -> list[list[int]]
        :param SignalHeads_num_inboundL: inbound干线左转灯头编号 -> list[list[int]]
        :param SignalHeads_num_outboundL: outbound干线左转灯头编号 -> list[list[int]]
        :param SignalHeads -> e.g. [[arg1[int], arg2[int]], ...] index = 0 为 SGByNumber，index = 1 为 SignalHeadByNumber
        （2）input Signal Timing Plan
        实例化后设置属性
        : set attribute phase_inbound: outbound干线路段编号 -> list[int]
        : set attribute phase_outbound: outbound干线路段编号 -> list[int]
        : set attribute controllers_num: outbound干线路段编号 -> list[int]
        : set attribute cycle: outbound干线路段编号 -> list[int]
        : set attribute offset: outbound干线路段编号 -> list[int]
        : set attribute inter_location_inbound: outbound干线路段编号 -> list[int]
        : set attribute inter_location_outbound: outbound干线路段编号 -> list[int]
        : set attribute ari_signal_plan_ring1: outbound干线路段编号 -> list[int]
        : set attribute ari_signal_plan_ring2: outbound干线路段编号 -> list[int]
        """
        # 初始化
        self.fig = None
        self.period = period
        self.gw_speed = gw_speed
        self.cycle = None
        self.controllers_num = None
        self.phase_inbound = phase_inbound
        self.phase_outbound = phase_outbound
        self.inter_location_inbound = None
        self.inter_location_outbound = None
        self.ari_signal_plan_ring1 = None
        self.ari_signal_plan_ring2 = None
        self.ari_signal_plan_ring2_hatch = None
        self.ari_signal_plan_ring1_hatch = None
        self.ari_signal_plan_ring2_color = None
        self.ari_signal_plan_ring1_color = None
        self.arterial_length = None
        self.lanelength_inbound = None
        self.lanelength_outbound = None
        # 读取控制机数量及相位时长、相位差
        self.controllers_num, self.cycle, self.offset = None, None, None
        # 读取交叉口位置、车道数
        self.inter_location_inbound, self.inter_lane_num_inbound = None, None
        self.inter_location_outbound, self.inter_lane_num_outbound = None, None
        # 使用Vissim数据
        if LoadNet_name is not None:
            super().__init__(LoadNet_name, LoadLayout_name)
            self.period = period
            self.phase_inbound = phase_inbound
            self.phase_outbound = phase_outbound
            # 读取路段长度
            self.lanelength_inbound = self.lane_length(link_num_inbound)
            self.lanelength_outbound = self.lane_length(link_num_outbound)
            # 读取控制机数量及相位时长、相位差
            self.controllers_num, self.cycle, self.offset = self.get_controller()
            # 读取配时方案
            self.ari_signal_plan_ring1 = self.get_signalplan(SignalHeads_num_outbound, SignalHeads_num_inboundL,
                                                             phase_inbound)
            self.ari_signal_plan_ring2 = self.get_signalplan(SignalHeads_num_inbound, SignalHeads_num_outboundL,
                                                             phase_outbound)
            # 读取交叉口位置、车道数
            self.inter_location_inbound, \
                self.inter_lane_num_inbound = self.loc_arterial_intersection(link_num_inbound,
                                                                             SignalHeads_num_inbound, 'inbound')
            self.inter_location_outbound, \
                self.inter_lane_num_outbound = self.loc_arterial_intersection(link_num_outbound,
                                                                              SignalHeads_num_outbound, 'outbound')

            # print(self.inter_location_inbound, self.inter_lane_num_inbound)
            # print(self.inter_location_outbound, self.inter_lane_num_outbound)
            # print(self.ari_signal_plan_ring1)
            # print(self.ari_signal_plan_ring2)

    # 绘制配时方案
    def set_figure_attribute(self,
                             figsize: tuple = (20 / 2.54, 9),
                             dpi: int = 300,
                             facecolor=None,
                             edgecolor=None,
                             frameon=False) -> None:
        """
        用于设置输出图像大小，分辨率
        :param figsize: 图像尺寸 -> tuple[int]  默认值：(19, 9)
        :param dpi: 分辨率 -> float  默认值：100
        :param facecolor: 设置图形窗口的背景颜色 -> 颜色字符串或 RGB 值
        :param edgecolor: 设置图形窗口边缘的颜色 -> 颜色字符串或 RGB 值
        :param frameon: 是否显示图形窗口的框架 -> bool
        :return:
        """
        self.fig.set_dpi(dpi)
        self.fig.set_size_inches(figsize)
        self.fig.set_frameon(frameon)
        if facecolor is not None:
            self.fig.set_facecolor(facecolor)
        if edgecolor is not None:
            self.fig.set_edgecolor(edgecolor)

    @staticmethod
    def set_title(title: str = None, fontsize: int = 23) -> None:
        """
        定义标题
        :param title: -> str
        :param fontsize: 字符大小默认25
        :return:
        """
        # 定义标题
        if title is not None:
            transplt.suptitle(title, fontsize=fontsize)

    @staticmethod
    def _set_rcParams(x_rcParams: str = 'in', y_rcParams: str = 'in', font_style: str = 'SimSun') -> None:
        """
        设置刻度方向：
                    'in'：刻度朝内
                    'out'：刻度朝外
                    'inout'：刻度线同时朝内和朝外，这种情况下刻度线看起来可能会很短，就像没有刻度线一样
        :param x_rcParams: -> str 默认朝内
        :param y_rcParams: -> str 默认朝内
        :param font_style: -> str 字体默认'Times New Roman'
        :return: None
        """
        transplt.rcParams['font.family'] = font_style
        transplt.rcParams['xtick.direction'] = x_rcParams
        transplt.rcParams['ytick.direction'] = y_rcParams

    def set_show_lim(self, xlim: list = None, ylim: list = None) -> None:
        """
        图框显示区间
        :param xlim: list[int]，默认[1800, 2500]
        :param ylim: list[int]，默认干线长度
        :return: None
        """
        if ylim is None:
            if self.lanelength_outbound is not None:
                ylim = [0, max(self.inter_location_inbound) + self.lanelength_outbound[-1]]
            else:
                ylim = [0, max(self.inter_location_inbound) + 300]  # 默认延长300
        if xlim is None:
            xlim = [1800, 2500]
        transplt.xlim(xlim[0], xlim[1])
        transplt.ylim(ylim[0], ylim[1])

    @staticmethod
    def set_label(ylabel: str = 'Distance (m)', xlabel: str = 'Time (s)', fontsize: int = 20) -> None:
        """
        x轴、y轴标签及字体大小
        :param ylabel: 默认 Distance (m)
        :param xlabel: 默认 Time (s)
        :param fontsize: 默认25
        :return: None
        """
        transplt.ylabel(ylabel, fontdict={'fontsize': fontsize})
        transplt.xlabel(xlabel, fontdict={'fontsize': fontsize})

    @staticmethod
    def set_tick_params(labelsize: int = 20) -> None:
        """
        设置刻度标签的字体大小
        :param labelsize: 默认大小20
        :return:None
        """
        transplt.tick_params(labelsize=labelsize)

    @staticmethod
    def _get_args(kwargs, keyword) -> dict:
        # 从 kwargs 中提取 keyword 的值
        return kwargs.get(keyword, None)  # 如果不存在，则默认为 None

    def _set_name(self, name: str) -> list[str]:
        # 生成交叉口名称列表
        return [f"{name}{i + 1}" for i in range(self.controllers_num)]

    def set_intersection_name(self, name='S') -> None:
        """
        交叉口名称
        :param name: 默认为 “S”
        :return: None
        """
        inter_name = self._set_name(name)
        transplt.yticks([(i + j) / 2 for i, j in zip(self.inter_location_inbound,
                                                     self.inter_location_outbound)], inter_name)

    @staticmethod
    def tight_layout(lf: float = 0.05, rt: float = 0.95, bm: float = 0.1, tp: float = 0.93) -> None:
        """
        图像布局
        :param lf:子图左边缘到图的左边缘的距离
        :param rt:子图右边缘到图的右边缘的距离
        :param bm:子图底边缘到图的底边缘的距离
        :param tp:子图顶边缘到图的顶边缘的距离
        :return: None
        """
        transplt.subplots_adjust(left=lf, right=rt, bottom=bm, top=tp)

    def _plot_parameters_default(self) -> None:
        """
        # 图片尺寸默认(19, 9)，分辨率100
        # 字体默认“Times New Roman”
        # 将x周的刻度线方向设置向内
        # 将y轴的刻度方向设置向内
        # 时间显示区间为1800~2500s
        # 交叉口名称命名默认“S”+str(intersection i)
        # 布局默认紧凑型，left=0.05, right=0.95, bottom=0.05, top=0.95
        # 图中字符大小默认20
        :return: None
        """
        # self.set_figure_attribute()
        self._set_rcParams()
        self.set_show_lim()
        self.set_label()
        self.set_intersection_name()
        self.tight_layout()
        transplt.tick_params(labelsize=20)

    def _creat_cyclenum(self, period_: int) -> int:
        return math.ceil(period_ / max(self.cycle))

    def _creat_iterate_value(self, base_cycle: list) -> list:
        return [i + j for i, j in zip(base_cycle, self.offset)]

    @staticmethod
    def _iterate_leftvalue(iterate_value: list, signal_time: list) -> list:
        return [i + j for i, j in zip(iterate_value, signal_time)]

    def _barh_state(self, sbar_width: int,
                    inter_location: list, state: str,
                    signal_time: list, iterate_value: list,
                    ari_signal_plan_ring_color: dict,
                    ari_signal_plan_ring_hatch: dict) -> None:

        transplt.barh(inter_location, signal_time,
                      height=sbar_width, left=iterate_value,
                      color=ari_signal_plan_ring_color[state],
                      edgecolor=['r'] * self.controllers_num,
                      hatch=ari_signal_plan_ring_hatch[state],
                      linewidth=0)

    @staticmethod
    def _get_coordinate(iterate_value: list, inter_location: list, stright_green_time: list,
                        ari_signal_plan_ring: dict, index: int) -> tuple:
        """
        获取坐标
        :return: t1, d1, t2, d2, t3, d3, t4, d4
        """
        [t1, d1] = [iterate_value[index], inter_location[index]]
        [t2, d2] = [iterate_value[index + 1], inter_location[index + 1]]
        [t3, d3] = [iterate_value[index] + stright_green_time[index] + ari_signal_plan_ring['yr2'][index],
                    inter_location[index]]
        [t4, d4] = [
            iterate_value[index + 1] + stright_green_time[index + 1] + ari_signal_plan_ring['yr2'][index + 1],
            inter_location[index + 1]]

        return t1, d1, t2, d2, t3, d3, t4, d4

    @staticmethod
    def _get_nodal(gw_speed_: float, inter_location: list, coordinate_set: tuple, index: int) -> tuple:
        (t1, d1, t2, d2, t3, d3, t4, d4) = coordinate_set
        [a, b, c, d] = [(inter_location[index + 1] - d1) / gw_speed_ + t1,
                        (inter_location[index] - d2) / gw_speed_ + t2,
                        (inter_location[index + 1] - d3) / gw_speed_ + t3,
                        (inter_location[index] - d4) / gw_speed_ + t4]
        return a, b, c, d

    @staticmethod
    def _get_sl_green_time(phase_squence: list, ari_signal_plan_ring: dict) -> tuple[list[Any], list[Any]]:
        """
        获取直行路灯时长确定绿波带边界
        :return: straight_green_time, left_green_time
        """
        straight_green_time, left_green_time = [], []
        for i in range(len(phase_squence)):
            if phase_squence[i] == 'lead':
                straight_green_time.append(ari_signal_plan_ring['green2'][i])
                left_green_time.append(ari_signal_plan_ring['green1'][i])
            else:
                straight_green_time.append(ari_signal_plan_ring['green1'][i])
                left_green_time.append(ari_signal_plan_ring['green2'][i])
        return straight_green_time, left_green_time

    @staticmethod
    def _decide_band(coordinate_set: tuple, nodal_set: tuple):
        _, b, _, d = nodal_set
        t1, _, _, _, t3, _, _, _ = coordinate_set
        return [t3 - t1, t3 - b, d - t1, d - b]

    def _caltuate_bandwith(self, stamp: str, gw_speed_: float, inter_location: list,
                           iterate_value: list, index: int, ari_signal_plan_ring: dict) -> tuple[list, tuple, tuple]:
        """
        用于计算绿波带宽
        :param gw_speed_: 绿波速度（m/s） -> float
        :param iterate_value: 迭代变量 -> list
        :param index: 交叉口索引号 -> int
        :return: band_with: 带宽 -> float
                 coordinate_set：(t,d)坐标点 -> tuple
                 nodal_set: (a,b,c,d)交点 -> tuple
        """
        # 定义变量
        phase_sequence: list = self.phase_outbound if stamp == 'inbound' else self.phase_inbound
        # ari_signal_plan_ring: Any = self.ari_signal_plan_ring2 if stamp == 'inbound' else self.ari_signal_plan_ring1
        straight_green_time, left_green_time = self._get_sl_green_time(phase_sequence, ari_signal_plan_ring)
        iterate_value = [i + j for i, j in zip(iterate_value, ari_signal_plan_ring['yr1'])]

        # 判断对向左转是否前置，前置需在基底增加对向左转前置时间
        if phase_sequence[index] == 'lead':
            iterate_value[index] += left_green_time[index]
        if phase_sequence[index + 1] == 'lead':
            iterate_value[index + 1] += left_green_time[index + 1]
        if stamp == 'inbound':
            # 基底条件不满足，迭代器累加一个周期
            if self.offset[index + 1] <= self.offset[index]:
                if any(isinstance(x, list) for x in self.cycle):
                    iterate_value[index + 1] += self.cycle[index + 1][0]
                else:
                    iterate_value[index + 1] += self.cycle[index + 1]
        else:
            # 基底条件不满足，迭代器累加一个周期
            if self.offset[index + 1] >= self.offset[index]:
                if any(isinstance(x, list) for x in self.cycle):
                    iterate_value[index] += self.cycle[index][0]
                else:
                    iterate_value[index] += self.cycle[index]
        # 获取坐标
        coordinate_set: tuple = self._get_coordinate(iterate_value, inter_location, straight_green_time,
                                                     ari_signal_plan_ring, index)
        nodal_set: tuple = self._get_nodal(gw_speed_, inter_location, coordinate_set, index)
        # 计算带宽
        band_with: list = self._decide_band(coordinate_set, nodal_set)

        return band_with, coordinate_set, nodal_set

    @staticmethod
    def _decide_line(band_with: list, t_set: list, d_set: list) -> tuple:
        # t_1, t_2, t_3, t_4 = t_set
        # d_1, d_2, d_3, d_4 = d_set
        # transplt.plot(t_1, d_1, 'r', lw=0.5)
        # transplt.plot(t_2, d_2, 'g', lw=0.5)
        # transplt.plot(t_3, d_3, 'b', lw=0.5)
        # transplt.plot(t_4, d_4, 'y', lw=0.5)
        band = min(band_with)
        index_map = {0: (d_set[0], t_set[0]),
                     1: (d_set[1], t_set[1]),
                     2: (d_set[0], t_set[0]),
                     3: (d_set[1], t_set[1])}
        return index_map[band_with.index(band)], band

    def _plot_band_fill_betweenx(self, stamp: str, gw_speed_: float, band_with: list, coordinate_set: tuple,
                                 nodal_set: tuple, band_color: tuple, band_alpha: tuple) -> None:
        k = gw_speed_ / 3.6
        (t1, d1, t2, d2, t3, d3, t4, d4) = coordinate_set
        (a, b, c, d) = nodal_set
        t_set = [np.linspace(t1, a, 200), np.linspace(b, t2, 200), np.linspace(t3, c, 200), np.linspace(d, t4, 200)]
        d_set = [k * (t_set[0] - t1) + d1, k * (t_set[1] - t2) + d2, k * (t_set[2] - t3) + d3, k * (t_set[3] - t4) + d4]
        # 根据min(band_with)在band_with中的索引判断绿波带
        (d, t), band = self._decide_line(band_with, t_set, d_set)
        (color, alpha) = (band_color[0], band_alpha[0]) if stamp == 'inbound' else (band_color[1], band_alpha[1])
        transplt.fill_betweenx(d, t + band, t, color=color, alpha=alpha)

    def _plot_greenband(self, stamp: str, gw_speed: float, inter_location: list, iterate_value: list,
                        band_color: tuple, band_alpha: tuple, ari_signal_plan_ring: dict) -> list[str]:
        band_set = ['None' for _ in range(len(inter_location) - 1)]
        # 判断方向
        if stamp == 'inbound':
            for i in range(len(inter_location)):
                if i != len(inter_location) - 1:
                    """
                    (t1, d1, t2, d2, t3, d3, t4, d4) = coordinate_set
                    (a, b, c, d) = nodal_set
                    """
                    iterate = copy.deepcopy(iterate_value)
                    band_with, coordinate_set, nodal_set = self._caltuate_bandwith(stamp, gw_speed / 3.6,
                                                                                   inter_location, iterate, i,
                                                                                   ari_signal_plan_ring)
                    # 绘制inbound绿波带
                    if min(band_with) > 0:
                        band_set[i] = str(int(min(band_with))) + 's'
                        self._plot_band_fill_betweenx(stamp, gw_speed, band_with,
                                                      coordinate_set, nodal_set, band_color, band_alpha)
            return band_set

        else:
            for i in range(len(inter_location)):
                if i != len(inter_location) - 1:
                    iterate = copy.deepcopy(iterate_value)
                    band_with, coordinate_set, nodal_set = self._caltuate_bandwith(stamp, -gw_speed / 3.6,
                                                                                   inter_location, iterate, i,
                                                                                   ari_signal_plan_ring)
                    # 绘制outbound绿波带
                    if min(band_with) > 0:
                        band_set[i] = str(int(min(band_with))) + 's'
                        self._plot_band_fill_betweenx(stamp, -gw_speed, band_with,
                                                      coordinate_set, nodal_set, band_color, band_alpha)
            return band_set

    @staticmethod
    def _set_band_text(stamp: str, inter_location: list, band_set: list, time_loc: float, sbar_width: int,
                       fontsize: int) -> None:
        for i in range(len(band_set)):
            '''
            在time_loc的基础上向右平移了10个单位，inter_location的基础上分别移动了3倍和2倍
            '''
            if stamp == 'inbound':
                transplt.text(time_loc + 10, inter_location[i] - 3 * sbar_width, 'in_band=' + band_set[i],
                              fontdict={'fontsize': fontsize})
            else:
                transplt.text(time_loc + 10, inter_location[i + 1] + 2 * sbar_width, 'out_band=' + band_set[i],
                              fontdict={'fontsize': fontsize})

    @staticmethod
    def convert_ring(ring_data: dict) -> dict:
        """
        将ARI信号配时环1格式转换为环2格式
        """
        # 初始化目标数据结构
        ring = {
            'yr1': [],
            'green1': [],
            'yr2': [],
            'green2': [],
            'red': []
        }

        # 按相位顺序处理数据（S1 -> S4）
        for phase in sorted(ring_data.keys()):
            values = ring_data[phase]

            # 解包并填充数据（验证列表长度）
            if len(values) != 5:
                raise ValueError(f"相位 {phase} 的数据长度不正确，预期5个元素，实际得到{len(values)}个")

            ring['yr1'].append(values[0])  # 黄红灯时间1
            ring['green1'].append(values[1])  # 绿灯时间1
            ring['yr2'].append(values[2])  # 黄红灯时间2
            ring['green2'].append(values[3])  # 绿灯时间2
            ring['red'].append(values[4])  # 全红时间

        return ring

    def convert_adapt_ring(self, adapt_ring_data: list) -> list:
        """
        输出感应条件配时数据转换
        :param adapt_ring_data: 配时数据
        :return: 转换配时数据
        """
        for i in range(len(adapt_ring_data)):
            if set(adapt_ring_data[i].keys()) != {'yr1', 'green1', 'yr2', 'green2', 'red'}:  # 格式转换
                adapt_ring_data[i] = self.convert_ring(adapt_ring_data[i])
        return adapt_ring_data

    def convert_signalplan(self) -> Any:
        ari_signal_plan_ring1, ari_signal_plan_ring2 = None, None
        if type(self.ari_signal_plan_ring1) is dict:
            if set(self.ari_signal_plan_ring1.keys()) != {'yr1', 'green1', 'yr2', 'green2', 'red'}:  # 格式转换
                ari_signal_plan_ring1 = self.convert_ring(self.ari_signal_plan_ring1)
                ari_signal_plan_ring2 = self.convert_ring(self.ari_signal_plan_ring2)
        if type(self.ari_signal_plan_ring1) is list:
            ari_signal_plan_ring1 = self.convert_adapt_ring(self.ari_signal_plan_ring1)
            ari_signal_plan_ring2 = self.convert_adapt_ring(self.ari_signal_plan_ring2)

        return ari_signal_plan_ring1, ari_signal_plan_ring2

    def _barh_signal(self,
                     stamp: str,
                     band_fontsize: int,
                     plot_band: bool,
                     sbar_width: int,
                     base_cycle: list,
                     band_text: tuple,
                     period_: int,
                     gw_speed: float,
                     inter_location: list,
                     ari_signal_plan_ring: dict or list,
                     ari_signal_plan_ring_color: dict,
                     ari_signal_plan_ring_hatch: dict,
                     band_color: tuple, band_alpha: tuple) -> None:
        """
        绘制信号周期
        :param stamp: 用于判断方向 -> str
        :param band_fontsize: 设置text_band字符大小 -> int
        :param plot_band: 是否绘制绿波带 -> bool
        :param period_: 绘图周期 -> int
        :param gw_speed: 绿波速度 -> float
        :param base_cycle: cycle基底 -> list[int]
        :param inter_location: 停止线位置 -> list[int]
        :param ari_signal_plan_ring: 配时参数 -> dict[key[str]: value[float]]
                                                if fixed signal else list[dict[key[str]: value[float]]]
        :param ari_signal_plan_ring_color: 颜色参数 -> dict[key[str]: value[str]]
        :param ari_signal_plan_ring_hatch: 填充参数 -> dict[key[str]: value[str]]
        :param band_color: 绿波带颜色 -> tuple[str]
        :param band_alpha: 绿波带透明度 -> tuple[float]
        :param band_text: 绿波带带宽注释 -> bool
        :return:
        """
        band_set = ['None' for _ in range(len(inter_location) - 1)]
        # 判断输入模式
        if type(ari_signal_plan_ring) is dict:
            plot_cycle_num: int = self._creat_cyclenum(period_)  # 生成绘制周期数
            ari_signal_plan_ring = [ari_signal_plan_ring] * plot_cycle_num
        else:
            plot_cycle_num: int = len(ari_signal_plan_ring)

        iterate_value: list[int] = self._creat_iterate_value(base_cycle)  # 生成迭代变量
        for n in range(plot_cycle_num):
            # 绘制绿波带
            if plot_band and n > 0:
                # 从第二个周期开始绘制
                iterate_bvalue = copy.deepcopy(iterate_value)
                band_set = self._plot_greenband(stamp, gw_speed, inter_location, iterate_bvalue, band_color,
                                                band_alpha, ari_signal_plan_ring[n])
            #  读取配时方案
            for state, signal_time in ari_signal_plan_ring[n].items():
                #  绘制配时图
                self._barh_state(sbar_width,
                                 inter_location, state,
                                 signal_time, iterate_value,
                                 ari_signal_plan_ring_color,
                                 ari_signal_plan_ring_hatch)
                #  更新迭代变量
                iterate_value: list[int] = self._iterate_leftvalue(iterate_value, signal_time)
        # 添加带宽注释
        if plot_band and band_text[0]:
            self._set_band_text(stamp, inter_location, band_set, band_text[1], sbar_width, band_fontsize)

    def _base_cycle(self, cycle: list) -> list:
        if any(isinstance(x, list) for x in cycle):
            return [-max([cycle[i][0] for i in range(len(cycle))])] * self.controllers_num
        else:
            return [-max(cycle)] * self.controllers_num

    def _plot_signal_plan(self, sbar_width: int, plot_band: bool, band_color: tuple, band_alpha: tuple,
                          band_fontsize: int, band_text: tuple) -> None:
        """
        获取绘图对象
        :return: plot object
        """
        self._plot_parameters_default()  # 绘图参数默认
        # 生成cycle基底用于相位差调节
        base_cycle = self._base_cycle(self.cycle)
        # 绘制信号周期
        # 格式更新
        if (result := self.convert_signalplan()) != (None, None):
            self.ari_signal_plan_ring1, self.ari_signal_plan_ring2 = result

        self._barh_signal('inbound', band_fontsize, plot_band, sbar_width, base_cycle, band_text, self.period,
                          self.gw_speed, self.inter_location_inbound, self.ari_signal_plan_ring2,
                          self.ari_signal_plan_ring2_color, self.ari_signal_plan_ring2_hatch, band_color, band_alpha)
        self._barh_signal('outbound', band_fontsize, plot_band, sbar_width, base_cycle, band_text, self.period,
                          self.gw_speed, self.inter_location_outbound, self.ari_signal_plan_ring1,
                          self.ari_signal_plan_ring1_color, self.ari_signal_plan_ring1_hatch, band_color, band_alpha)

    @staticmethod
    def _get_plotargs(**kwargs) -> dict:
        # 定义默认值
        defaults = {
            'g_color': '#40fd14',
            'gl_color': '#40fd14',
            'r_color': 'r',
            'y_color': 'y',
            'g_hatch': '',
            'gl_hatch': 'xxx',
            'r_hatch': '',
            'y_hatch': '',
            'sbar_width': 20,
            'plot_band': True,
            'band_color': ('b', 'g'),
            'band_alpha': (0.2, 0.2),
            'band_fontsize': 13,
            'band_text': (False, 0)
        }
        return {key: kwargs.get(key, value) for key, value in defaults.items()}

    def _temp_data(self) -> list:
        temp_set = [self.ari_signal_plan_ring1_color,
                    self.ari_signal_plan_ring2_color,
                    self.ari_signal_plan_ring1_hatch,
                    self.ari_signal_plan_ring2_hatch]
        return temp_set

    def plot_signal_plan(self, /, **kwargs) -> None:
        """
        用于绘制配时方案
        :param: kwargs: 任意关键字参数
        Optional[str]:
                g_color: 直行绿灯颜色 -> str
                gl_color: 左转绿灯颜色 -> str
                r_color: 红灯颜色 -> str
                y_color: 黄灯颜色 -> str
                g_hatch:直行绿灯填充 -> [str]
                gl_hatch:左转绿灯填充 -> [str]
                r_hatch:红灯填充 -> [str]
                y_hatch:黄灯填充 -> [str]
                        参数填充：'' ：没有填充图案。
                        图案字符包括：
                                    '/'：斜线填充。
                                    '\\'：反斜线填充。
                                    '|'：竖线填充。
                                    '-'：横线填充。
                                    '+'：加号填充。
                                    'x'：叉号填充。
                                    'o'：圆圈填充。
                                    'O'：大圆圈填充。
                                    '.'：点状填充。
                                    '*'：星号填充。
                        组合使用，以创建更复杂的填充图案，如'/\\\\' 表示交替的斜线和反斜线填充。
                sbar_width: 信号灯带宽度，默认20 -> int
                plot_band: 是否绘制绿波带 -> bool
                band_color: 绿波带颜色，默认inbound -> 'b'，outbound -> 'g', -> tuple[str]
                band_alpha: 绿波带透明度，默认inbound -> 0.2，outbound -> 0.2 -> tuple[float]
                time_loc: 用于判断text_band横轴位置 -> float
                band_fontsize: 设置text_band字符大小 -> int
                band_text: 绿波带带宽注释 -> tuple
                            band_text[0]是否标记带宽，band_text[1]标记横轴位置
                            band_text[0] -> bool, band_text[1] -> float

        :return: None
        """
        # 初始化画布
        self.fig = transplt.figure(figsize=(19, 9), dpi=100)
        # 获取参数
        plot_args = self._get_plotargs(**kwargs)
        # 从plot_args中解构出各个参数
        g_color, gl_color, r_color, y_color = plot_args['g_color'], plot_args['gl_color'], \
            plot_args['r_color'], plot_args['y_color']
        g_hatch, gl_hatch, r_hatch, y_hatch = plot_args['g_hatch'], plot_args['gl_hatch'], \
            plot_args['r_hatch'], plot_args['y_hatch']
        sbar_width, plot_band = plot_args['sbar_width'], plot_args['plot_band']
        band_color, band_alpha = plot_args['band_color'], plot_args['band_alpha']
        band_fontsize, band_text = plot_args['band_fontsize'], plot_args['band_text']
        # 判断接入方式
        if None in self._temp_data():
            # 设置颜色为默认 # 颜色后面绘制时输入
            self.ari_signal_plan_ring1_color \
                = self.set_signal_color(self.phase_inbound, g_color, gl_color, r_color, y_color, self.controllers_num)
            self.ari_signal_plan_ring2_color \
                = self.set_signal_color(self.phase_outbound, g_color, gl_color, r_color, y_color, self.controllers_num)
            # 设置填充为默认 # 颜色后面绘制时输入
            self.ari_signal_plan_ring1_hatch \
                = self.set_left_signal_hatch(self.phase_inbound, g_hatch, gl_hatch, r_hatch, y_hatch,
                                             self.controllers_num)
            self.ari_signal_plan_ring2_hatch \
                = self.set_left_signal_hatch(self.phase_outbound, g_hatch, gl_hatch, r_hatch, y_hatch,
                                             self.controllers_num)
        # 绘制配时方案
        self._plot_signal_plan(sbar_width, plot_band, band_color, band_alpha, band_fontsize, band_text)

        # print(self.ari_signal_plan_ring1_color)
        # print(self.ari_signal_plan_ring2_color)
        # print(self.ari_signal_plan_ring1_hatch)
        # print(self.ari_signal_plan_ring2_hatch)

    # 绘制车辆轨迹
    def _plot_single_seed_trajectories(self, stamp: str,
                                       time_data: list, distance_data: list,
                                       color: str, linewidth: float) -> None:
        if self.lanelength_outbound is None:
            self.lanelength_inbound = [self.arterial_length]
            self.lanelength_outbound = [self.arterial_length]

        if stamp == 'inbound':
            for i in range(len(time_data)):
                transplt.plot(time_data[i], distance_data[i], color, linewidth=linewidth)
        else:
            for i in range(len(time_data)):
                tempst = [sum(self.lanelength_outbound) - j for j in distance_data[i]]
                transplt.plot(time_data[i], tempst, color, linewidth=linewidth)

    def plot_trajectories(self, inbound_tradata: dict, outbound_tradata: dict, /,
                          color: tuple[str] = ('#0485d1', '#0485d1'),
                          linewidth: tuple[float] = (0.1, 0.1)) -> None:
        """
        绘制车辆轨迹
        :param color: 轨迹颜色，默认 #0485d1  -> tuple[str[inbound_color], str[outbound_color]]
        :param linewidth: 轨迹线宽，默认 0.1 -> tuple[float[inbound_linewidth], float[outbound_linewidth]]
        :param inbound_tradata: inbound轨迹数据
                              -> dict{'seed': tuple(list[time_inbound], list[distance_inbound], list[speed_inbound])}
        :param outbound_tradata: outbound轨迹数据
                              -> dict{'seed': tuple(list[time_outbound], list[distance_outbound], list[speed_outbound)}
            -----------------------------------------------------------------------------------------------------------
                time_：时间戳集合 -> list[list[single_vehicle_time_stamp[float]], ...]
                distance_：位置戳集合 -> list[list[single_vehicle_distance_stamp[float]], ...]
                speed_：速度戳集合 -> list[list[single_vehicle_speed_stamp[float]], ...]
            -----------------------------------------------------------------------------------------------------------
        :return: None
        """
        for key, value in inbound_tradata.items():
            self._plot_single_seed_trajectories('inbound', value[0], value[1], color[0], linewidth[0])
        for key, value in outbound_tradata.items():
            self._plot_single_seed_trajectories('outbound', value[0], value[1], color[0], linewidth[0])


class PurduePlot(SignalPlanPlot):
    """
    绘制普渡图
    """

    def __init__(self, /, cycle: list = None, offset: list = None, arterial_length=None,
                 inter_location_inbound: list = None, inter_location_outbound: list = None,
                 inbound_tradata: dict = None, outbound_tradata: dict = None,
                 phase_inbound: list = None, phase_outbound: list = None,
                 ari_signal_plan_ring1: dict = None, ari_signal_plan_ring2: dict = None,
                 purdue_data: tuple[dict, dict] = None):
        """
        初始化绘制普渡图原始数据 datastore模块获取或直接设置属性
        :param cycle: 实例化datastore模块中 AterialDataCollection，通过 get_controller 方法得到
        :param offset: 实例化datastore模块中 AterialDataCollection，通过 get_controller 方法得到
        :param arterial_length: 实例化datastore模块中 AterialDataCollection，通过 lane_length 方法得到 -> list
        :param arterial_length: outbound方向路径长度
                                    if lanelength_outbound =  None，input sum_length_outbound -> float
        :param inter_location_outbound: 实例化datastore模块中 AterialDataCollection，通过 loc_arterial_intersection 方法得到
        :param inter_location_outbound: 实例化datastore模块中 AterialDataCollection，通过 loc_arterial_intersection 方法得到
        :param phase_inbound: 上行相序 -> list[str]
        :param phase_outbound: 下行相序 -> list[str]
        :param ari_signal_plan_ring1: 配时数据ring1 -> dict
        :param ari_signal_plan_ring2: 配时数据ring2 -> dict
        ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
        # 数据来源： ①轨迹数据 or ②普渡数据
        :param inbound_tradata: inbound轨迹数据
                              -> dict{'seed': tuple(list[time_inbound], list[distance_inbound], list[speed_inbound])}
        :param outbound_tradata: outbound轨迹数据
                              -> dict{'seed': tuple(list[time_outbound], list[distance_outbound], list[speed_outbound)}
            -----------------------------------------------------------------------------------------------------------
                time_：时间戳集合 -> list[list[single_vehicle_time_stamp[float]], ...]
                distance_：位置戳集合 -> list[list[single_vehicle_distance_stamp[float]], ...]
                speed_：速度戳集合 -> list[list[single_vehicle_speed_stamp[float]], ...]
            -----------------------------------------------------------------------------------------------------------
        :param purdue_data: 车辆到达数据，若输入则直接基于车辆数据进行普渡图输出
                            当purdue_data=None时，应当输入轨迹数据和交叉口位置信息进行分析得到车辆到达数据
                            -> tuple[dict{str[seed]: inbound_purdue_data}, dict{str[seed]: outbound_purdue_data}]
                            -> dict{str[seed]: dict{s_num: tuple[tuple[list[net_time], list[arrive_time]]]}}
        """
        # 初始化画布
        super().__init__()
        # End Of Green and Begin Of Green
        self.seed_num = None
        self.outbound_BOG_EOG = None
        self.inbound_BOG_EOG = None
        self.label = None
        self.purdue_data = purdue_data
        self.cycle, self.offset = cycle, offset
        if self.purdue_data is None:
            self.inter_location_inbound = inter_location_inbound
            self.inter_location_outbound = inter_location_outbound
            self.inbound_tradata = inbound_tradata
            self.outbound_tradata = outbound_tradata
            self.phase_inbound = phase_inbound
            self.phase_outbound = phase_outbound
            self.ari_signal_plan_ring1 = ari_signal_plan_ring1
            self.ari_signal_plan_ring2 = ari_signal_plan_ring2
            if type(arterial_length) is not list:
                self.lanelength_outbound = [arterial_length]
            else:
                self.lanelength_outbound = arterial_length

        else:
            self.purdue_data_inbound, self.purdue_data_outbound = self.purdue_data
            self.lanelength_outbound = [arterial_length]
            self.phase_inbound = phase_inbound
            self.phase_outbound = phase_outbound
            self.ari_signal_plan_ring1 = ari_signal_plan_ring1
            self.ari_signal_plan_ring2 = ari_signal_plan_ring2

    @staticmethod
    def set_label(ylabel: str = 'Time in cycle (s)', xlabel: str = 'Time (s)', fontsize: int = 12) -> None:
        """
        x轴、y轴标签及字体大小
        :param ylabel: 默认 Time in cycle (s)
        :param xlabel: 默认 Time (s)
        :param fontsize: 默认25
        :return: None
        """
        transplt.ylabel(ylabel, fontdict={'fontsize': fontsize})
        transplt.xlabel(xlabel, fontdict={'fontsize': fontsize})

    def _plot_parameters_default(self) -> None:
        """
        # 图片尺寸默认(5, 5)，分辨率100
        # 字体默认“Times New Roman”
        # 将x周的刻度线方向设置向内
        # 将y轴的刻度方向设置向内
        # 布局默认紧凑型，left=0.05, right=0.95, bottom=0.05, top=0.95
        # 图中字符大小默认20
        :return: None
        """
        self._set_rcParams()
        self.set_label()
        transplt.tick_params(labelsize=12)

    # 绘制普渡图
    @staticmethod
    def _creat_cantiner(inter_loc: list):
        return ([[] for _ in range(len(inter_loc))] for _ in range(2))

    @staticmethod
    def find_interval(net_time: float, cycle: list):
        # 生成累积和列表add_cycle
        add_cycle = list(itertools.accumulate(cycle))
        # 处理空列表的情况
        if not add_cycle:
            raise ValueError("Cycle list is empty")
        # 检查a是否在有效范围内
        max_value = add_cycle[-1]
        if net_time < 0 or net_time > max_value:
            raise ValueError(f"a={net_time} is out of the valid range [0, {max_value}]")
        # 使用bisect_right找到插入位置
        i = bisect.bisect_right(add_cycle, net_time)
        # 返回区间索引
        return i - 1, i

    def _output_purdue_data(self, stamp: str, time_stamp: list, distance_stamp: list) -> dict:
        """
        将轨迹数据转换成车辆到达数据
        :param time_stamp: 轨迹数据路网时间戳 -> list[list[float, ...], ...]
        :param distance_stamp: 轨迹数据距离时间戳 -> list[list[float, ...], ...]
        :return: 车辆周期内时间戳，路网时间戳 -> dict{"intersection_number": tuple[list[float], list[float]], ...}
                return的数据outbound方向数据为反向数据，即第一组数据对应干线方向最后一个交叉口
        """
        if stamp == 'inbound':
            inter_loc: list = self.inter_location_inbound
        else:
            self.inter_location_outbound.reverse()
            self.offset.reverse()
            inter_loc: list = [sum(self.lanelength_outbound) - i_loc for i_loc in self.inter_location_outbound]
        net_time, arrive_time = self._creat_cantiner(inter_loc)
        purdue_data = {}  # 初始化数据存储容器
        for i_num in range(len(inter_loc)):
            for i in range(len(time_stamp)):
                dist_temp: list = distance_stamp[i]
                # 寻找距离路口最近的点判断POG
                posPCD = min(dist_temp, key=lambda temp: abs(temp - (inter_loc[i_num] - 20)))
                net_time[i_num].append(time_stamp[i][dist_temp.index(posPCD)])
                # find interval base_cycle
                if any(isinstance(x, list) for x in self.cycle):
                    _, index_sum = self.find_interval(time_stamp[i][dist_temp.index(posPCD)], self.cycle[i_num])
                    cycle = self.cycle[i_num][index_sum]
                else:
                    cycle = self.cycle[i_num]
                arrive_time[i_num].append(
                    (time_stamp[i][dist_temp.index(posPCD)] - self.offset[i_num]) % cycle)

            # 存储单个交叉口数据
            if stamp == 'inbound':
                purdue_data.setdefault(f'S{i_num + 1}', (net_time[i_num], arrive_time[i_num]))
            else:
                purdue_data.setdefault(f'S{len(inter_loc) - i_num}', (net_time[i_num], arrive_time[i_num]))

        return purdue_data

    @staticmethod
    def _creat_cantiner_dict() -> list[dict[Any, Any]]:
        return [{} for _ in range(2)]

    def _data_processing(self) -> tuple:
        """
        用于数据处理
        :return: 普渡数据 -> dict{seed: dict{s_num: tuple[tuple[list[net_time], list[arrive_time]]]}}
        """
        # 生成存储容器
        purdue_data_inbound, purdue_data_outbound = self._creat_cantiner_dict()
        # 读取数据
        for key, value in self.inbound_tradata.items():
            purdue_data_in = self._output_purdue_data('inbound', value[0], value[1])
            purdue_data_inbound.setdefault(key, purdue_data_in)
        for key, value in self.outbound_tradata.items():
            purdue_data_out = self._output_purdue_data('outbound', value[0], value[1])
            purdue_data_outbound.setdefault(key, purdue_data_out)

        return purdue_data_inbound, purdue_data_outbound

    @staticmethod
    def _get_plotargs(**kwargs) -> dict:
        # 定义默认值
        defaults = {
            'title_language': "E",
            'label': ('inbound', 'outbound'),
            'size_dot': 0.3,
            'color_dot': 'b',
            'fontsize': 13,
            'POG': True
        }
        return {key: kwargs.get(key, value) for key, value in defaults.items()}

    def _plot_axhline(self, begin_of_green: float, end_of_green: float, index: int, base_and_cycle: Any) -> None:

        if base_and_cycle is not None:
            label_BOG_EOG = ['BOG', 'EOG'] if self.plt_label is True else [None, None]
            transplt.hlines(y=begin_of_green, xmin=base_and_cycle[1], xmax=sum(base_and_cycle), color='green',
                            label=label_BOG_EOG[0])
            transplt.hlines(y=end_of_green, xmin=base_and_cycle[1], xmax=sum(base_and_cycle), color='red',
                            label=label_BOG_EOG[1])
            transplt.legend(loc='upper right')
            self.plt_label = False
        else:
            transplt.axhline(y=begin_of_green, color='green', label='BOG')
            transplt.axhline(y=end_of_green, color='red', label='EOG')
            transplt.legend(loc='upper right')
            transplt.ylim(0, math.ceil(self.cycle[index] / 5) * 5)

    def _plot_BOG_EOG(self, ari_signal_plan_ring: dict, phase_: list, index: int, base_and_cycle=None) -> tuple:

        begin_of_green, end_of_green = 0, 0
        if ari_signal_plan_ring is not None:
            phase = phase_[index]
            if phase == 'lag':
                begin_of_green = ari_signal_plan_ring['yr1'][index]
                end_of_green = begin_of_green + ari_signal_plan_ring['green1'][index]
                self._plot_axhline(begin_of_green, end_of_green, index, base_and_cycle)

            else:
                begin_of_green = ari_signal_plan_ring['yr1'][index] + \
                                 ari_signal_plan_ring['green1'][index] + \
                                 ari_signal_plan_ring['yr2'][index]
                end_of_green = begin_of_green + ari_signal_plan_ring['green2'][index]
                self._plot_axhline(begin_of_green, end_of_green, index, base_and_cycle)
        return begin_of_green, end_of_green

    @staticmethod
    def find_index_bound(data, bound):
        left, right = bound
        start = bisect.bisect_left(data, left)
        end = bisect.bisect_right(data, right) - 1
        # 始终返回长度为2的列表，用 -1 标记无效区间
        return [start, end] if start <= end else [None, None]

    def _percent_on_green(self, value_sum: list, bound_BOG_EOG: Any):
        """
        计算POG
        :param value_sum: dict{s_num: tuple[tuple[list[net_time], list[arrive_time]]]}
        :param bound_BOG_EOG: tuple[(BOD, EOG), ...] or list[(当前周期bog_eog:tuple, 当前周期叠加时间, 当前周期时长), ...]
        :return:
        """
        pog = []
        if type(bound_BOG_EOG) is list:
            # bound_BOG_EOG: list -> [(bog_eog, base_cycle, cycle), ...]
            for value_sum_seed in value_sum:  # value_sum_seed -> tuple[tuple[list[net_time], list[arrive_time]]]
                # 获取车辆在那个周期区间内 共有len([(当前周期bog_eog:tuple, 当前周期叠加时间, 当前周期时长), ...])个周期
                low_bound = 0
                for n in range(len(bound_BOG_EOG)):
                    # value_sum_seed[0] -> list[net_time]
                    # 找到时间片段  bound_BOG_EOG[n][0][1] -> EOG
                    [start, end] = self.find_index_bound(value_sum_seed[0], [low_bound, bound_BOG_EOG[n][1]])
                    low_bound += bound_BOG_EOG[n][2]

                    if start != end:
                        # value_sum_seed[1] -> list[arrive_time]
                        count = sum(1 for arrival_time in value_sum_seed[1][start:end] if
                                    bound_BOG_EOG[n][0][0] <= arrival_time <= bound_BOG_EOG[n][0][1])
                        pog.append(count / len(value_sum_seed[1][start:end]))
                    # else:
                    #     break
        else:
            # bound_BOG_EOG: tuple
            for value_sum_seed in value_sum:
                count = sum(1 for arrival_time in value_sum_seed[1] if
                            bound_BOG_EOG[0] <= arrival_time <= bound_BOG_EOG[1])
                pog.append(count / len(value_sum_seed[1]))

        return sum(pog) / len(pog) if len(pog) != 0 else 0  # 返回 percent on green

    def _process_timedata(self, veh_ID_data, k):
        arrivel_time = [i + k * self.period for i in veh_ID_data[0]]
        return arrivel_time, veh_ID_data[1]

    @staticmethod
    def _cal_cycle(ring: dict, index: int) -> float:
        """
        计算感应控制下周期时长
        :return: 数据采集周期
        """
        return sum(values[index] for values in ring.values())

    def _judge_bog_eog(self, ari_signal_plan_ring, phase_outbound, index_):
        """
        判断控制模式：固定 or 感应
        :return: BOG_EOG -> tuple[(BOD, EOG), ...] or list[(当前周期bog_eog:tuple, 当前周期叠加时间 ， 当前周期时长), ...]
        """
        if type(ari_signal_plan_ring) is list:
            BOG_EOG = []
            base_cycle = 0  # 基底线
            for ring in ari_signal_plan_ring:
                cycle = self._cal_cycle(ring, index_)
                bog_eog: tuple = self._plot_BOG_EOG(ring, phase_outbound, index_, [cycle, base_cycle])
                base_cycle += cycle
                BOG_EOG.append((bog_eog, base_cycle, cycle))

            transplt.ylim(0, 180)  # 默认区间为180s
        else:
            BOG_EOG = self._plot_BOG_EOG(ari_signal_plan_ring, phase_outbound, index_)

        return BOG_EOG

    def _plot_purdue(self, purdue_data: dict, size_dot: float, color_dot: str, label: str, title: str,
                     fontsize: int, POG: bool) -> tuple[Any, Any]:
        """
        :param purdue_data: dict{str[seed]: dict{s_num: tuple[tuple[list[net_time], list[arrive_time]]]}}
        :return: bound_BOG_EOG
        """
        # 将字典的键转换为列表
        keys_list = list(purdue_data.keys())
        # 设置BOG、EOG存储容器
        bound_BOG_EOG, _ = self._creat_cantiner_dict()

        for key_sum, value_sum in purdue_data.items():  # 第key下有i个list用于存储不同种子下的车辆到达数据
            self._plot_parameters_default()  # 绘图参数默认
            for veh_ID_data in value_sum:
                # 后移seed*period, k 第k个种子
                veh_ID_data = self._process_timedata(veh_ID_data, value_sum.index(veh_ID_data))
                transplt.scatter(veh_ID_data[0], veh_ID_data[1], s=size_dot, color=color_dot)

            transplt.title(f'{key_sum} Purdue Coordination Diagram', fontsize=fontsize) if title == "E" \
                else transplt.title(f'{key_sum} 普渡图', fontsize=fontsize)

            if label is not None:
                transplt.legend(label, loc='upper right')
            transplt.xlim(0, self.period * self.seed_num)

            # End Of Green and Begin Of Green
            if label == self.label[0]:
                # inbound
                self.plt_label = True  # 图例
                index_ = keys_list.index(key_sum)
                BOG_EOG = self._judge_bog_eog(self.ari_signal_plan_ring2, self.phase_outbound, index_)

            else:
                # outbound
                self.plt_label = True  # 图例
                index_ = len(keys_list) - (keys_list.index(key_sum) + 1)
                BOG_EOG = self._judge_bog_eog(self.ari_signal_plan_ring1, self.phase_outbound, index_)
            bound_BOG_EOG.setdefault(f'S{index_ + 1}', BOG_EOG)

            if POG:
                percent_on_green = self._percent_on_green(value_sum, BOG_EOG)
                transplt.text(0.05, 0.95, f'{label} POG = {round(percent_on_green * 100, 2)}%',
                              transform=transplt.gca().transAxes,
                              horizontalalignment='left',
                              verticalalignment='top',
                              color='green')

            transplt.show()
            # transplt.close('all')

        return bound_BOG_EOG

    def _consolidation_data(self, data: dict) -> dict:
        arterial_data_set, s_num_set = self._creat_cantiner_dict()
        arterial_data_set.setdefault('arterial', s_num_set)
        # 遍历data中的每个键（a, b, c）
        for key in data:
            # 遍历每个键下的值
            for k, v in data[key].items():
                # 如果newdata中的data键不存在，则创建一个空列表
                if k not in arterial_data_set["arterial"]:
                    arterial_data_set["arterial"][k] = []
                # 将当前值添加到对应的列表中
                arterial_data_set["arterial"][k].append(v)

        return arterial_data_set

    def plot_purdue(self, /, **kwargs):
        """
        绘制普渡图
        :param kwargs:
                        title_language："C" or "E" -> str
                        label: 标签名 -> tuple[str[inbound_label], str[outbound_label]], “无” -> None
                        size_dot: 散点大小 -> float
                        color_dot: 散点颜色 -> str
                        POG: percent on green -> bool
        :return: None
        """
        # 格式转换
        # 格式更新
        if (result := self.convert_signalplan()) != (None, None):
            self.ari_signal_plan_ring1, self.ari_signal_plan_ring2 = result
        # 获取参数
        plot_args = self._get_plotargs(**kwargs)
        title, self.label, fontsize = plot_args['title_language'], plot_args['label'], plot_args['fontsize']
        size_dot, color_dot, POG = plot_args['size_dot'], plot_args['color_dot'], plot_args['POG']

        if self.purdue_data is None:
            self.purdue_data_inbound, self.purdue_data_outbound = self._data_processing()

        # 绘图
        self.seed_num = len(self.purdue_data_inbound)
        # 多个随机种子数据需合并
        self.purdue_data_inbound = self._consolidation_data(self.purdue_data_inbound)
        self.purdue_data_outbound = self._consolidation_data(self.purdue_data_outbound)
        for key, purdue_data in self.purdue_data_inbound.items():
            self.inbound_BOG_EOG = self._plot_purdue(purdue_data, size_dot, color_dot,
                                                     self.label[0], title, fontsize, POG)
        for key, purdue_data in self.purdue_data_outbound.items():
            self.outbound_BOG_EOG = self._plot_purdue(purdue_data, size_dot, color_dot,
                                                      self.label[1], title, fontsize, POG)

    # 存储普渡数据
    def save_purdue_data(self, file_location):
        if self.purdue_data is None:
            purdue_data = (self.purdue_data_inbound, self.purdue_data_outbound)
            save_variable(purdue_data, 'purdue_data', file_location)
        purdue_BOG_EOG = (self.inbound_BOG_EOG, self.outbound_BOG_EOG)
        save_variable(purdue_BOG_EOG, 'purdue_BOG_EOG', file_location)


if __name__ == '__main__':
    print('used for plot diagram')
    tra = SignalPlanPlot()  # 实例化
    tra.gw_speed = 50  # 绿波速度
    tra.phase_inbound = ['lead', 'lag']  # 设置相序
    tra.phase_outbound = ['lag', 'lag']
    # 设置信号机个数，周期，相位差
    tra.controllers_num, tra.cycle, tra.offset = 2, [148, 148], [0, 96]
    tra.inter_location_inbound = [154, 1271]  # 上行交叉口进口道停止线位置
    tra.inter_location_outbound = [202, 1347]  # 下行交叉口进口道停止线位置
    # 设置配时方案
    tra.ari_signal_plan_ring1 = {'yr1': [3, 2], 'green1': [29, 43],
                                 'yr2': [2, 2], 'green2': [39, 37], 'red': [75, 64]}
    tra.ari_signal_plan_ring2 = {'yr1': [3, 2], 'green1': [43, 39],
                                 'yr2': [2, 2], 'green2': [25, 41], 'red': [75, 64]}
    tra.plot_signal_plan(band_text=(True, 1800))  # 绘制配时图
    transplt.show()
