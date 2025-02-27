# A CASE FOR EXAMPLE OF HOW TO GET TRAJECTORY DATA FROM VIS-SIM FOR RATING, NOTE: THE VIS-SIM VERSION USED HERE IS
# VIS-SIM 4.3. For any inquiries, please contact Cheney Zhao at cheneyzhao@126.com. This software is the intellectual
# property of Cheney Zhao at WUST (Wuhan University of Science and Technology).


import win32com.client as com
from getdata import GetVisTrajectoryData
from systrajectorylib.ratedata import RateData
from datastore import load_variavle
from systrajectorylib.rateperformance import output_POG, output_stop_percent, output_average_speed, \
    RateCoordinationPerformance, output_seed_speed, output_stop_delay
from transplotlib import *


def exp():
    # ////////////////////////////////////////获取数据//////////////////////////////////////////////////
    getdata = GetVisTrajectoryData(LoadNet_name, LoadLayout_name, link_num_inbound, link_num_outbound, seed=[10, 10],
                                   period=3600)
    inbound_trajectorydata, outbound_trajectorydata = getdata.get_vis_trajectorydata()
    Vissim = com.Dispatch("VISSIM.vissim.430")
    Vissim.Exit()
    # 存储轨迹数据
    save_variable(inbound_trajectorydata, 'inbound_trajectorydata', 'D:\\CSPT\\TrajectiesData')
    save_variable(outbound_trajectorydata, 'outbound_trajectorydata', 'D:\\CSPT\\TrajectiesData')
    # ///////////////////////////////////////////////////////////////////////////////////////////////

    # /////////////////////////////////读取路网数据///////////////////////////////////////////////////
    datas = AterialDataCollection(LoadNet_name, LoadLayout_name)  # 实例化路网数据采集
    controllers_num, cycle, offset = datas.get_controller()  # 获取交叉口个数、周期时长、相位差
    lanelength_outbound = datas.lane_length(link_num_outbound)  # 下行路段长度
    # 读取配时方案
    ari_signal_plan_ring1 = datas.get_signalplan(SignalHeads_num_outbound, SignalHeads_num_inboundL, phase_inbound)
    ari_signal_plan_ring2 = datas.get_signalplan(SignalHeads_num_inbound, SignalHeads_num_outboundL, phase_outbound)
    # 读取交叉口位置、车道数
    inter_location_in, inter_lane_num_in = datas.loc_arterial_intersection(link_num_inbound, SignalHeads_num_inbound,
                                                                           'inbound')
    inter_location_out, inter_lane_num_out = datas.loc_arterial_intersection(link_num_outbound,
                                                                             SignalHeads_num_outbound, 'outbound')
    arterial_length = datas.lane_length(link_num_outbound)  # 计算干线长度
    # ////////////////////////////////////////////////////////////////////////////////////////////////

    # /////////////////////////////////////////评价///////////////////////////////////////////////////
    # 存储评价数据
    RD = RateData(inbound_trajectorydata, inter_location_in, 0)  # 实例化
    inbound_rate_data = RD.output_rate_data()
    RD = RateData(outbound_trajectorydata, inter_location_out, 0, arterial_length)
    outbound_rate_data = RD.output_rate_data()
    # 存储评价数据
    inbound_rate_data = save_variable(inbound_rate_data, 'inbound_rate_data', 'D:\\CSPT\\RateData')
    outbound_rate_data = save_variable(outbound_rate_data, 'outbound_rate_data', 'D:\\CSPT\\RateData')
    # 组合
    ratedata = (inbound_rate_data, outbound_rate_data)
    lane_arterial = (inter_lane_num_in, inter_lane_num_out)
    inter_location = (inter_location_in, inter_location_out)
    per = RateCoordinationPerformance(ratedata, inter_location, inter_traffic_volume, ari_traffic_volume,
                                      lane_arterial, lane_side)
    per.cycle = cycle
    per.ari_signal_plan_ring1 = ari_signal_plan_ring1
    per.ari_signal_plan_ring2 = ari_signal_plan_ring2
    in_ave_speed_seed, out_ave_speed_seed, _, _ = per.output_performance_grade()
    # ///////////////////////////////////////////////////////////////////////////////////////////////////////

    # //////////////////////////////////////////绘图//////////////////////////////////////////////////
    tra = SignalPlanPlot(LoadNet_name, LoadLayout_name,
                         link_num_inbound, link_num_outbound,
                         phase_inbound, phase_outbound,
                         SignalHeads_num_inbound, SignalHeads_num_outbound,
                         SignalHeads_num_inboundL, SignalHeads_num_outboundL, gw_speed=50)
    tra.plot_signal_plan(band_text=(True, 1800))
    # 绘制轨迹
    tra.plot_trajectories(inbound_trajectorydata, outbound_trajectorydata)
    transplt.show()
    # 绘制普渡图
    pu = PurduePlot(cycle=cycle, offset=offset, arterial_length=lanelength_outbound)
    pu.inter_location_inbound = inter_location_in
    pu.inter_location_outbound = inter_location_out
    pu.inbound_tradata = inbound_trajectorydata
    pu.outbound_tradata = outbound_trajectorydata
    pu.ari_signal_plan_ring1 = ari_signal_plan_ring1
    pu.ari_signal_plan_ring2 = ari_signal_plan_ring2
    pu.phase_inbound = phase_inbound
    pu.phase_outbound = phase_outbound
    # ///////////////////////////////////////////绘制普渡图////////////////////////////////////////
    pu.plot_purdue()
    # 存储普渡数据
    pu.save_purdue_data('D:\\CSPT\\PurdueData')  # 存储purdue_data、purdue_BOG_EOG
    (purdue_data1, purdue_data2) = load_variavle('D:\\CSPT\\PurdueData\\purdue_data.pkl')
    (purdue_BOG_EOG1, purdue_BOG_EOG2) = load_variavle('D:\\CSPT\\PurdueData\\purdue_BOG_EOG.pkl')
    print('============================================================================')
    a = output_POG(purdue_data1, purdue_BOG_EOG1)
    b = output_POG(purdue_data2, purdue_BOG_EOG2)
    print('============================================================================')
    print(f'average POG: ', (a + b) / 2)
    print('============================================================================')
    aa = output_stop_percent(inter_location_in, inbound_trajectorydata, 0)
    bb = output_stop_percent(inter_location_out, outbound_trajectorydata, 0)
    print('============================================================================')
    print(f'average stop percent: ', (aa + bb) / 2)
    print('============================================================================')
    # ////////////////////////////////////////////////////////////////////////////////////////////////

    # /////////////////////////////////////////输出数据/////////////////////////////////////////////
    output_average_speed(inbound_rate_data, 'inbound', 'D:\\CSPT\\OUTPUT_Data')
    output_average_speed(outbound_rate_data, 'outbound', 'D:\\CSPT\\OUTPUT_Data')
    output_seed_speed(in_ave_speed_seed, 'inbound', 'D:\\CSPT\\OUTPUT_Data')
    output_seed_speed(out_ave_speed_seed, 'outbound', 'D:\\CSPT\\OUTPUT_Data')
    output_stop_delay(inbound_rate_data, controllers_num, 'inbound', 'D:\\CSPT\\OUTPUT_Data')
    output_stop_delay(outbound_rate_data, controllers_num, 'outbound', 'D:\\CSPT\\OUTPUT_Data')


if __name__ == "__main__":
    LoadNet_name = 'D:\\CSPT\\p_road1.inp'
    LoadLayout_name = 'D:\\CSPT\\p_road1.in0'
    lane_side = [3, 5, 5, 3]
    ari_traffic_volume = (1311, 1790)
    inter_traffic_volume = ([1311, 866, 1430, 1806], [1480, 1788, 1012, 1790])
    # 干线路段编号
    link_num_inbound = [1, 10001, 2, 10035, 12, 10009, 13, 17, 10012, 18, 10014, 19, 10015, 20, 10055,
                        27, 10024, 35, 10025, 36, 10066, 37, 10030, 47, 10031, 46, 10073, 51]
    link_num_outbound = [6, 10000, 5, 10037, 14, 10006, 9, 10054, 30, 10021, 29, 10020, 28, 10067, 50,
                         10033, 49, 10032, 48, 10074, 52]
    # 干线直行灯头编号 [0]为SGByNumber，[1]为SignalHeadByNumber
    SignalHeads_num_inbound = [[5, 2], [5, 18], [5, 46], [4, 64]]
    SignalHeads_num_outbound = [[2, 4], [1, 1], [1, 27], [2, 57]]
    # 干线左转灯头编号
    SignalHeads_num_inboundL = [[1, 1], [2, 220], [2, 33], [1, 54]]
    SignalHeads_num_outboundL = [[6, 6], [6, 20], [6, 47], [5, 67]]
    # 相序根据该方向左转前置后置确定
    phase_inbound = ['lead', 'lag', 'lag', 'lead']
    phase_outbound = ['lag', 'lag', 'lag', 'lag']
    exp()
