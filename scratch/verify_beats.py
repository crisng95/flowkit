# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding='utf-8')

original = """Chương 10: Không Gian Không Tên. Họ bắt đầu đi xuống lòng đất vào lúc sáng sớm ngày mười hai tháng chín — bốn ngày sau khi Tiểu Kỳ đột ngột xuất hiện ở cửa căn hộ của anh giữa đêm muộn hai giờ sáng, và ba ngày kể từ khi Sable mở lối terminal tự ý thức đầu tiên để chạm vào nhận thức của anh. Bản tin nhắn của Tiểu Kỳ gửi vào tối hôm trước ngắn gọn đến mức tối giản: “Anh sẵn sàng chưa?” Hùng chỉ phản hồi lại hai chữ: “Sáng mai.” Giữa họ đã hình thành một kiểu thỏa thuận ngầm không lời. Không cần những lời giải thích thừa thãi, không cần những cam kết rườm rà. Trong bầu không khí ngột ngạt của Omega-7, sự im lặng mang nhiều trọng lượng hơn bất kỳ từ ngữ nào. Họ gặp nhau tại điểm đầu của con đường kỹ thuật chạy dọc rìa Zone 4. Đây chính là nơi hai tuần trước, Trần Thiên Ân đã đứng lặng lẽ trong bóng tối ẩm ướt của đêm muộn, dán mắt vào cánh cổng thép của trạm DN-31 để tìm kiếm một dấu vết vô hình. Hùng đến điểm hẹn lúc sáu giờ mười hai phút sáng. Tiểu Kỳ đã ở đó từ trước. Cô ngồi lặng lẽ trên thanh chắn kim loại gỉ sét đã bong tróc hết lớp sơn bảo ôn, chiếc ba lô vải dù sờn rách đặt ngay dưới chân. Đôi mắt cô hướng về phía đông, nơi đường chân trời đang chuyển dần từ màu xám đục sang một vệt cam nhạt nhòa thiếu sức sống — cái thứ ánh sáng rỉ ra từ bộ lọc khí công nghiệp của thành phố trong một buổi sớm tháng chín. “Anh mang theo những gì?” cô hỏi, giọng nói phẳng lặng, không hề quay đầu lại. “Sổ tay giấy. Đèn pin LED. Thiết bị đo tần số cầm tay ngoại tuyến,” Hùng dừng lại một nhịp ngắn, bàn tay vỗ nhẹ vào túi áo khoác kaki dày. “Và nước uống.” “Tốt.” Cô đứng dậy, cúi xuống xách chiếc ba lô lên vai. “Đừng ghi chép bất kỳ điều gì vào thiết bị điện tử khi chúng ta ở bên dưới. Chỉ dùng sổ giấy và bút chì.” Hùng nhíu mày dưới gọng kính kim loại mỏng. “Tại sao?” “Có một thứ trường lực đặc biệt trong đó. Nó không phá hủy phần cứng, nhưng nó sẽ làm nhiễu loạn các ô nhớ. Mọi dữ liệu số anh lưu lại bên dưới sẽ tự động biến mất hoặc biến dạng thành các chuỗi ký tự rác ngay khi anh bước trở lại mặt đất.” Cô chỉnh lại quai đeo ba lô, ánh mắt lạnh lùng quét qua chiếc điện thoại đang tắt nguồn trong túi anh. “Tôi đã thử. Nhiều lần. Không có ngoại lệ.” Hùng nhìn cô chăm chú. Gương mặt cô vẫn giữ nguyên vẻ nhợt nhạt đặc trưng của những người sống dưới tầng tối, nhưng trong đôi mắt đen sâu thẳm kia không có chỗ cho sự mơ hồ. “Cô đã thử bằng thiết bị gì?”"""

beats = [
    "Chương 10: Không Gian Không Tên. Họ bắt đầu đi xuống lòng đất vào lúc sáng sớm ngày mười hai tháng chín — ",
    "bốn ngày sau khi Tiểu Kỳ đột ngột xuất hiện ở cửa căn hộ của anh giữa đêm muộn hai giờ sáng, và ba ngày kể từ khi Sable mở lối terminal tự ý thức đầu tiên để chạm vào nhận thức của anh. ",
    "Bản tin nhắn của Tiểu Kỳ gửi vào tối hôm trước ngắn gọn đến mức tối giản: “Anh sẵn sàng chưa?” Hùng chỉ phản hồi lại hai chữ: “Sáng mai.” Giữa họ đã hình thành một kiểu thỏa thuận ngầm không lời. ",
    "Không cần những lời giải thích thừa thãi, không cần những cam kết rườm rà. Trong bầu không khí ngột ngạt của Omega-7, sự im lặng mang nhiều trọng lượng hơn bất kỳ từ ngữ nào. ",
    "Họ gặp nhau tại điểm đầu của con đường kỹ thuật chạy dọc rìa Zone 4. ",
    "Đây chính là nơi hai tuần trước, Trần Thiên Ân đã đứng lặng lẽ trong bóng tối ẩm ướt của đêm muộn, dán mắt vào cánh cổng thép của trạm DN-31 để tìm kiếm một dấu vết vô hình. ",
    "Hùng đến điểm hẹn lúc sáu giờ mười hai phút sáng. Tiểu Kỳ đã ở đó từ trước. ",
    "Cô ngồi lặng lẽ trên thanh chắn kim loại gỉ sét đã bong tróc hết lớp sơn bảo ôn, chiếc ba lô vải dù sờn rách đặt ngay dưới chân. ",
    "Đôi mắt cô hướng về phía đông, nơi đường chân trời đang chuyển dần từ màu xám đục sang một vệt cam nhạt nhòa thiếu sức sống — cái thứ ánh sáng rỉ ra từ bộ lọc khí công nghiệp của thành phố trong một buổi sớm tháng chín. ",
    "“Anh mang theo những gì?” cô hỏi, giọng nói phẳng lặng, không hề quay đầu lại. ",
    "“Sổ tay giấy. Đèn pin LED. Thiết bị đo tần số cầm tay ngoại tuyến,” Hùng dừng lại một nhịp ngắn, bàn tay vỗ nhẹ vào túi áo khoác kaki dày. “Và nước uống.” ",
    "“Tốt.” Cô đứng dậy, cúi xuống xách chiếc ba lô lên vai. “Đừng ghi chép bất kỳ điều gì vào thiết bị điện tử khi chúng ta ở bên dưới. Chỉ dùng sổ giấy và bút chì.” ",
    "Hùng nhíu mày dưới gọng kính kim loại mỏng. “Tại sao?” ",
    "“Có một thứ trường lực đặc biệt trong đó. Nó không phá hủy phần cứng, nhưng nó sẽ làm nhiễu loạn các ô nhớ. ",
    "Mọi dữ liệu số anh lưu lại bên dưới sẽ tự động biến mất hoặc biến dạng thành các chuỗi ký tự rác ngay khi anh bước trở lại mặt đất.” ",
    "Cô chỉnh lại quai đeo ba lô, ánh mắt lạnh lùng quét qua chiếc điện thoại đang tắt nguồn trong túi anh. “Tôi đã thử. Nhiều lần. Không có ngoại lệ.” ",
    "Hùng nhìn cô chăm chú. Gương mặt cô vẫn giữ nguyên vẻ nhợt nhạt đặc trưng của những người sống dưới tầng tối, nhưng trong đôi mắt đen sâu thẳm kia không có chỗ cho sự mơ hồ. “Cô đã thử bằng thiết bị gì?”"
]

reconstructed = "".join(beats)
if reconstructed == original:
    print("Match: SUCCESS")
else:
    print("Match: FAILURE")
    print("Reconstructed len:", len(reconstructed))
    print("Original len:", len(original))
    for idx, (a, b) in enumerate(zip(reconstructed, original)):
        if a != b:
            print(f"Mismatch at index {idx}: reconstructed={repr(reconstructed[idx:idx+20])}, original={repr(original[idx:idx+20])}")
            break
