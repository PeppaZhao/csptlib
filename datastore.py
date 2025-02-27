"""
初始化数据 从VIS-SIM路网中获取路网数据

Author: CheneyZhao.wust.edu
           cheneyzhao@126.com
"""
from typing import Any
import math
import win32com.client as com
import pickle


# 从“.pkl”文件读取数据
def load_variavle(file_location: str):
    """
    读取“.pkl”文件
    :param file_location: 文件位置（包含文件名.pkl） -> str
    :return: None
    """
    try:
        with open(file_location, 'rb') as f:
            data = pickle.load(f)
            f.close()  # 关闭文件，释放内存。
        return data

    except EOFError:
        return ""


# 储存数据
def save_variable(v, name: str, file_location: str):
    """
    用于储存轨迹数据
    :param name: 变量名称 -> str
    :param file_location: 储存文件位置
    :param v: inbound_traydata or outbound_tradata -> dict
    :return: 输出.pkl文件
    """
    file = file_location + '\\' + name + '.pkl'
    f = open(file, 'wb')  # 打开或创建名叫filename的文档。
    pickle.dump(v, f)  # 在文件filename中写入v
    f.close()  # 关闭文件，释放内存。
    return v


class AterialDataCollection:

    def __init__(self, LoadNet_name: str = None, LoadLayout_name: str = None):
        self.LoadLayout_name = LoadNet_name
        self.LoadNet_name = LoadLayout_name
        if LoadNet_name is not None:
            self.LoadNet_name = LoadNet_name
            self.LoadLayout_name = LoadLayout_name
            self.Vissim = com.Dispatch("VISSIM.vissim.430")
            self.Vissim.LoadNet(self.LoadNet_name)
            self.Vissim.LoadLayout(self.LoadLayout_name)
            self.Sim = self.Vissim.Simulation
            self.vnet = self.Vissim.net
            self.links = self.vnet.Links
            self.controllers = self.vnet.SignalControllers

    # 读取干线路径长度
    def _get_length(self, Lane_num: list) -> float:
        return self.links.GetLinkByNumber(Lane_num).AttValue('LENGTH')

    def lane_length(self, link_num_set: list) -> list:
        """
        :param link_num_set: 干线路段编号->list
        :return: 路段长度
        """
        lanelength = []  # 路段长度
        for Lane_num in link_num_set:
            lanelength.append(self._get_length(Lane_num))

        return lanelength

    # 读取信号机信息

    @staticmethod
    def set_phase_sequences(interphase: list, signalheads_num: list, signalHeads_num_left: list) -> list:
        """
        用于相序排列配时顺序
        :param interphase: [[arg[str]]
        :param signalheads_num: 干线直行灯头编号[[arg1[int], arg2[int]]]，[0]为SGByNumber，[1]为SignalHeadByNumber
        :param signalHeads_num_left: 干线左转灯头编号[[arg1[int], arg2[int]]]，[0]为SGByNumber，[1]为SignalHeadByNumber
        :return: signalheads ->list[list[int]]
        """
        signalheads = [[] for _ in range(len(signalheads_num))]
        for i in range(len(interphase)):
            if interphase[i] == 'lead':
                signalheads[i].append(signalHeads_num_left[i])
                signalheads[i].append(signalheads_num[i])
            else:
                signalheads[i].append(signalheads_num[i])
                signalheads[i].append(signalHeads_num_left[i])

        return signalheads

    @staticmethod
    def _get_offset(controllers, i: int) -> int:
        return math.ceil(controllers.GetSignalControllerByNumber(i).AttValue('OFFSET'))

    @staticmethod
    def _get_cycle(controllers, i: int) -> int:
        return math.ceil(controllers.GetSignalControllerByNumber(i).AttValue('CYCLETIME'))

    def _get_controllers_num(self) -> int:
        return self.vnet.SignalControllers.Count

    def get_controller(self) -> tuple[int, list[int], list[int]]:
        """
        :return: 返回系统信号机对象
        """
        cycle_, offset_ = [], []

        controllers_num_ = self._get_controllers_num()

        for i in range(1, controllers_num_ + 1):
            offset_.append(self._get_offset(self.controllers, i))
            cycle_.append(self._get_cycle(self.controllers, i))

        return controllers_num_, cycle_, offset_

    # 读取信号配时
    @staticmethod
    def _get_redtime(cycle_: int, yr1: int, green1: int, yr2: int, green2: int) -> int:
        return cycle_ - yr1 - green1 - yr2 - green2

    @staticmethod
    def _get_redend(SG_num) -> int:
        return SG_num.AttValue('REDEND')

    @staticmethod
    def _get_greenend(SG_num) -> int:
        return SG_num.AttValue('GREENEND')

    def _get_greentime(self, SG_num) -> int:

        GREEN = self._get_greenend(SG_num) - self._get_redend(SG_num)

        return GREEN

    @staticmethod
    def _get_yellowtime(SG_num) -> int:

        YELLOW = SG_num.AttValue('AMBER')
        return YELLOW

    def _get_SGnum(self, signalheads_num, i):
        SG_num = self.controllers.GetSignalControllerByNumber(
            i + 1).SignalGroups.GetSignalGroupByNumber(signalheads_num)
        return SG_num

    def _get_yr2(self, SG_num1, SG_num2):
        yr2 = self._get_redend(SG_num2) - self._get_greenend(SG_num1)

        return yr2

    @staticmethod
    def _creat_cantiner_list() -> list[list]:

        return [[] for _ in range(5)]

    @staticmethod
    def _ch(cor: str, controllers_num_: int):

        return [cor] * controllers_num_

    def _creat_ch(self, arg1: str, arg2: str, controllers_num_: int) -> tuple:

        b1_ch = self._ch(arg2, controllers_num_)
        y_a_ch = self._ch(arg2, controllers_num_)
        r_ch = self._ch(arg1, controllers_num_)

        return r_ch, b1_ch, y_a_ch

    @staticmethod
    def _creat_phase_sequences(interphase: list, awg1: str, awg2: str) -> tuple[list[Any], list[Any]]:
        set1, set2 = [], []
        for i in range(len(interphase)):
            if interphase[i] == 'lead':
                set1.append(awg2)
                set2.append(awg1)
            else:
                set1.append(awg1)
                set2.append(awg2)

        return set1, set2

    def get_signalplan(self, signalheads_num: list, signalHeads_num_left: list, interphase: list) -> Any:
        """
        灯头编号[[arg[int], arg[int]]]每一交叉口同一进口道方向任取其一灯头即可
        :param signalheads_num: 干线直行灯头编号[[arg[int], arg[int]]]，[0]为SGByNumber，[1]为SignalHeadByNumber
        :param signalHeads_num_left: 干线左转灯头编号[[arg[int], arg[int]]]，[0]为SGByNumber，[1]为SignalHeadByNumber
        :param interphase: 交叉口相序 [str]
        :return: 采用NEMA相位设置:
           ---------------------------------------------------------------------------------------------------------
           yr1    +     green1(in)     +    yellow/allred    +     green2(out)     +     barrier2     +     red
           ---------------------------------------------------------------------------------------------------------
           yr1    +     green1(out)     +    yellow/allred    +     green2(in)     +     barrier2     +     red
           ---------------------------------------------------------------------------------------------------------
                :returns：arterial_signal_plan -> dict[str, list[int]]
                yr1[int]、green[int]、yr2[int]、greenL[int]、barrier2[int]、red[int]
        """
        yr1, yr2, green1, green2, red = self._creat_cantiner_list()
        controllers_num_, cycle_, offset_ = self.get_controller()

        # 联立相序
        signalheads = self.set_phase_sequences(interphase, signalheads_num, signalHeads_num_left)

        # 读取配时数据
        for i in range(controllers_num_):
            SG_num1 = self._get_SGnum(signalheads[i][0][0], i)  # 获取第一个相位灯头编号对象
            # yellow = self._get_yellowtime(SG_num1)  # 黄灯时长
            # 获取yr1及绘制配色
            yr1.append(self._get_redend(SG_num1))

            # 获取green1
            green1.append(self._get_greentime(SG_num1))

            # 获取yr2
            SG_num2 = self._get_SGnum(signalheads[i][1][0], i)  # 获取第二个相位灯头编号对象
            yr2.append(self._get_yr2(SG_num1, SG_num2))

            # 获取green2
            green2.append(self._get_greentime(SG_num2))
            # 获取barrier2 + red
            red.append(self._get_redtime(cycle_[i], yr1[i], green1[i], yr2[i], green2[i]))

        # 封装干线配时数据
        arterial_signal_plan = {'yr1': yr1, 'green1': green1, 'yr2': yr2,
                                'green2': green2, 'red': red}
        return arterial_signal_plan

    # 设置干线配时图颜色
    def set_signal_color(self, interphase: list, /,
                         g_color: str = '#40fd14', gl_color: str = '#40fd14', r_color: str = 'r', y_color: str = 'y',
                         controllers_num: int = None):
        """
        默认值：g_color='#40fd14', gl_color='#40fd14', r_color='r', y_color='y'
           :param controllers_num: 控制机个数, 不使用Vis-sim时需输入当前干线系统交叉口个数 -> int
           :param interphase: 交叉口相序 [str]
           :param g_color: 直行绿灯颜色 -> str
           :param gl_color: 左转绿灯颜色 -> str
           :param r_color: 红灯颜色 -> str
           :param y_color: 黄灯颜色 -> str
           :return: arterial_signal_plan_color
        """
        if controllers_num is None:
            if None not in [self.LoadNet_name, self.LoadLayout_name]:
                controllers_num, _, _ = self.get_controller()
            elif controllers_num is None:
                print("Error in controllers_num setting")  # 打印错误信息
                raise ValueError("Error in controllers_num setting")

        r_color, b1_color, y_a_color = self._creat_ch(r_color, y_color, controllers_num)
        g1_color, g2_color = self._creat_phase_sequences(interphase, g_color, gl_color)

        # 封装干线配时配色
        arterial_signal_plan_color = {'yr1': b1_color, 'green1': g1_color, 'yr2': y_a_color,
                                      'green2': g2_color, 'red': r_color}

        return arterial_signal_plan_color

    # 设置灯组填充
    def set_left_signal_hatch(self, interphase: list, /,
                              g_hatch: str = '', gl_hatch: str = 'xxx', r_hatch: str = '', y_hatch: str = '',
                              controllers_num: int = None) -> dict:
        """
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
        :param controllers_num:
        :param interphase:交叉口相序 [str]
        :param g_hatch:直行绿灯填充 [str]
        :param gl_hatch:左转绿灯填充 [str]
        :param r_hatch:红灯填充 [str]
        :param y_hatch:黄灯填充 [str]
        :return:left_signal_hatch
        """
        if controllers_num is None:
            if None not in [self.LoadNet_name, self.LoadLayout_name]:
                controllers_num, _, _ = self.get_controller()
            elif controllers_num is None:
                print("Error in controllers_num setting")  # 打印错误信息
                raise ValueError("Error in controllers_num setting")
        r_hatch, b1_hatch, y_a_hatch = self._creat_ch(r_hatch, y_hatch, controllers_num)
        g1_hatch, g2_hatch = self._creat_phase_sequences(interphase, g_hatch, gl_hatch)

        # 封装干线配时配色
        left_signal_hatch = {'yr1': b1_hatch, 'green1': g1_hatch, 'yr2': y_a_hatch,
                             'green2': g2_hatch, 'red': r_hatch}
        return left_signal_hatch

    # 获取干线交叉口位置信息、交叉口进口道车道数
    def _get_intersection_info(self, signalheads_num: list, i: int, value: str) -> int:
        """
        这里正向输入了i作为信号机索引，当方向输入不正确存在Error
        """
        SG_num = self._get_SGnum(signalheads_num[i][0], i)  # 获取相位灯头编号对象
        intersection_info = SG_num.SignalHeads.GetSignalHeadByNumber(signalheads_num[i][1]).AttValue(value)

        return intersection_info

    @staticmethod
    def _find_link_index(link_num_set: list, link_num: int) -> int:

        return link_num_set.index(link_num)

    def _get_intersection_lane_num(self, signalheads_num: list, i: int) -> int:
        link_num_info = self._get_intersection_info(signalheads_num, i, 'LINK')
        return self.vnet.Links.GetLinkByNumber(link_num_info).AttValue('NUMLANES')

    @staticmethod
    def _get_intersection_location(lane_length_set: list, location: float, index: int, direction: str) -> float:

        if direction == 'inbound':
            if index == 0:
                return location
            else:
                return location + sum(lane_length_set[:index])
        elif direction == 'outbound':
            return lane_length_set[index] - location + sum(lane_length_set[:index])
        else:
            print("Error input of direction: Expected 'inbound' or 'outbound'")
            raise ValueError("Error input of direction: 'inbound' or 'outbound'")

    def loc_arterial_intersection(self, link_num_set: list, signalheads_num: list, direction: str) -> tuple:
        """
        用于获取交叉口位置
        :param signalheads_num: 干线直行方向灯头编号 -> list[list[int]]
        :param link_num_set: 干线直行方向灯头编号 -> list[int]
        :param direction: 输入方向，'inbound' or 'outbound' -> str
        :return: 灯头所在路段对应编号位置、位置、车道数 inter_location[float], inter_lane_num[int]
                 inter_location -> list[int], inter_lane_num -> list[int]
        """
        inter_location, inter_lane_num = [], []
        for i in range(len(signalheads_num)):
            # 获取交叉口直行灯头的link number
            link_num = self._get_intersection_info(signalheads_num, i, 'LINK')
            # 获取交叉口进口道车道数
            inter_lane_num.append(self._get_intersection_lane_num(signalheads_num, i))
            index = self._find_link_index(link_num_set, link_num)
            # 获取交叉口在当前link上的位置
            location = self._get_intersection_info(signalheads_num, i, 'LINKCOORD')

            lane_length_set = self.lane_length(link_num_set)
            # 获取当前交叉口位置并添加至交叉口集合
            inter_location.append(self._get_intersection_location(lane_length_set, location, index, direction))

        return inter_location, inter_lane_num


if __name__ == "__main__":
    print('for data collection by vis sim')
