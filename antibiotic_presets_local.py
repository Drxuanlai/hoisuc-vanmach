# antibiotic_presets_local.py
# Phác đồ kháng sinh kinh nghiệm dạng khung.
# Bệnh viện/khoa có thể chỉnh file này theo antibiogram và phác đồ nội bộ.

ANTIBIOTIC_PROTOCOLS = {
    "Viêm phổi cộng đồng nặng": {
        "base_coverage": [
            "Phế cầu và tác nhân hô hấp cộng đồng thường gặp",
            "Gram âm hô hấp thường gặp",
            "Tác nhân không điển hình",
        ],
        "base_suggestion": [
            "Beta-lactam theo phác đồ bệnh viện + macrolide",
            "Hoặc beta-lactam + respiratory fluoroquinolone nếu phù hợp",
        ],
        "mdr_addon": [
            "Nếu nguy cơ Pseudomonas: chọn beta-lactam có phổ kháng Pseudomonas theo phác đồ bệnh viện",
            "Nếu nguy cơ MRSA: thêm thuốc anti-MRSA theo phác đồ bệnh viện",
            "Nếu nguy cơ ESBL cao và sốc: cân nhắc carbapenem theo phác đồ bệnh viện",
        ],
        "cultures": ["Cấy máu 2 bộ", "Cấy đàm hoặc hút đàm nếu đặt nội khí quản", "X-quang/CT ngực nếu ổn định"],
        "source_control": "Tìm biến chứng cần dẫn lưu/kiểm soát nguồn: mủ màng phổi, áp xe phổi, ổ nhiễm ngoài phổi."
    },
    "Viêm phổi bệnh viện / ICU / VAP": {
        "base_coverage": [
            "Gram âm bệnh viện",
            "Pseudomonas nếu có nguy cơ hoặc ICU có tỷ lệ cao",
            "MRSA nếu có nguy cơ hoặc dịch tễ khoa phù hợp",
        ],
        "base_suggestion": [
            "Anti-pseudomonal beta-lactam theo phác đồ HAP/VAP của bệnh viện",
            "Thêm anti-MRSA khi có nguy cơ MRSA hoặc tỷ lệ MRSA tại khoa cao",
        ],
        "mdr_addon": [
            "Cân nhắc phối hợp hai thuốc kháng Pseudomonas nếu sốc và nguy cơ kháng thuốc cao theo antibiogram",
            "Cân nhắc Acinetobacter/CRE nếu có tiền sử cấy hoặc dịch tễ ICU",
        ],
        "cultures": ["Cấy máu 2 bộ", "Cấy hút nội khí quản/BAL nếu có", "Đánh giá catheter/ổ nhiễm khác"],
        "source_control": "Đánh giá VAP, catheter, dịch màng phổi, áp xe và các ổ nhiễm bệnh viện khác."
    },
    "Nhiễm khuẩn tiết niệu phức tạp / Pyelonephritis": {
        "base_coverage": [
            "Enterobacterales",
            "Gram âm niệu thường gặp",
        ],
        "base_suggestion": [
            "Cephalosporin thế hệ 3 hoặc beta-lactam/beta-lactamase inhibitor theo phác đồ bệnh viện",
        ],
        "mdr_addon": [
            "Nếu nguy cơ ESBL/MDR hoặc sốc: cân nhắc carbapenem theo phác đồ bệnh viện",
            "Nếu nghi Pseudomonas: chọn thuốc có phổ Pseudomonas theo phác đồ",
        ],
        "cultures": ["Cấy máu 2 bộ", "Cấy nước tiểu trước kháng sinh nếu không trì hoãn", "Siêu âm/CT nếu nghi tắc nghẽn"],
        "source_control": "Loại trừ tắc nghẽn đường niệu, áp xe thận/quanh thận, sonde nhiễm khuẩn cần thay/rút."
    },
    "Nhiễm khuẩn ổ bụng": {
        "base_coverage": [
            "Gram âm đường ruột",
            "Kỵ khí",
            "Enterococcus trong một số bối cảnh bệnh viện/ICU",
        ],
        "base_suggestion": [
            "Beta-lactam/beta-lactamase inhibitor theo phác đồ bệnh viện",
            "Hoặc cephalosporin + metronidazole nếu phù hợp phác đồ địa phương",
        ],
        "mdr_addon": [
            "Nếu nguy cơ ESBL/MDR hoặc sốc: cân nhắc carbapenem theo phác đồ bệnh viện",
            "Nếu nhiễm bệnh viện/ổ bụng phức tạp: cân nhắc Enterococcus và nấm theo nguy cơ",
        ],
        "cultures": ["Cấy máu 2 bộ", "Cấy dịch ổ bụng nếu dẫn lưu/phẫu thuật", "CT bụng khi ổn định"],
        "source_control": "Source control là trọng tâm: dẫn lưu ổ mủ, phẫu thuật, xử trí thủng/tắc, ERCP nếu nhiễm trùng đường mật."
    },
    "Da - mô mềm nặng": {
        "base_coverage": [
            "Streptococcus",
            "Staphylococcus aureus",
            "Gram âm/kỵ khí nếu hoại tử, đái tháo đường hoặc nhiễm vùng tầng sinh môn",
        ],
        "base_suggestion": [
            "Phác đồ bệnh viện cho nhiễm da mô mềm nặng",
            "Thêm anti-MRSA nếu có nguy cơ hoặc bệnh cảnh nặng",
        ],
        "mdr_addon": [
            "Nếu nghi viêm cân mạc hoại tử: cần phẫu thuật khẩn, phối hợp kháng sinh rộng theo phác đồ",
            "Cân nhắc độc tố liên cầu/tụ cầu theo bệnh cảnh",
        ],
        "cultures": ["Cấy máu 2 bộ", "Cấy mô/dịch mủ sâu nếu có", "Không trì hoãn phẫu thuật nếu nghi hoại tử"],
        "source_control": "Rạch dẫn lưu, cắt lọc mô hoại tử, hội chẩn ngoại khoa sớm."
    },
    "Nhiễm khuẩn huyết liên quan catheter": {
        "base_coverage": [
            "Staphylococcus aureus/coagulase-negative staphylococci",
            "Gram âm bệnh viện tùy bối cảnh",
            "Candida nếu nguy cơ cao",
        ],
        "base_suggestion": [
            "Anti-MRSA + bao phủ Gram âm theo phác đồ bệnh viện nếu sốc",
            "Cân nhắc kháng nấm nếu nguy cơ Candida cao",
        ],
        "mdr_addon": [
            "Mở rộng phổ theo tiền sử cấy MDR và antibiogram khoa",
        ],
        "cultures": ["Cấy máu 2 bộ ngoại biên", "Cấy máu qua catheter nếu có thể", "Cấy đầu catheter khi rút"],
        "source_control": "Cân nhắc rút/thay catheter nghi nhiễm, đặc biệt khi sốc, S. aureus, Candida hoặc nhiễm dai dẳng."
    },
    "Chưa rõ ổ nhiễm": {
        "base_coverage": [
            "Cần bao phủ rộng theo bối cảnh cộng đồng/bệnh viện và mức độ sốc",
            "Tìm ổ nhiễm song song: phổi, niệu, bụng, da-mô mềm, catheter, thần kinh trung ương",
        ],
        "base_suggestion": [
            "Dùng phác đồ sepsis/septic shock chưa rõ ổ của bệnh viện",
            "Ưu tiên coverage đủ rộng ban đầu nếu sốc, sau đó xuống thang khi có dữ kiện",
        ],
        "mdr_addon": [
            "Mở rộng phổ nếu có nguy cơ MDR/MRSA/Pseudomonas/ESBL hoặc nhiễm bệnh viện",
        ],
        "cultures": ["Cấy máu 2 bộ", "Cấy nước tiểu", "Cấy đàm nếu triệu chứng hô hấp", "Cấy dịch/mủ/catheter theo lâm sàng"],
        "source_control": "Tìm ổ cần can thiệp bằng khám lại, POCUS, X-quang/CT và hội chẩn chuyên khoa."
    },
}

