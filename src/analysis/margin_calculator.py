def calculate_customs_and_margin(price_cny, exchange_rate=190, shipping_fee_krw=7000, is_b2b=False):
    """
    1688 위안화 상품 가격을 기반으로 실무 통관 공식 및 최종 소싱 원가를 계산합니다.
    
    Args:
        price_cny: 1688 위안화 가격
        exchange_rate: 현재 위안-원 환율 (기본값 190원)
        shipping_fee_krw: 예상 배대지 배송비 (기본값 7,000원)
        is_b2b: 사입 여부 (True: 대량 사입 / False: 개인 구매대행)
        
    Returns:
        dict: 상세 계산 내역 (원화 가격, 관세, 부가세, 수수료, 최종 원가)
    """
    price_krw = price_cny * exchange_rate  # 물품대금 (원화)
    
    duty = 0
    vat = 0
    brokerage_fee = 0
    
    # 1. 통관비용 계산 로직
    if is_b2b:
        # [대량 사입 모드] 무조건 관/부가세 + 관세사 수수료 발생
        duty = int(price_krw * 0.08)  # 관세 8%
        vat = int((price_krw + duty) * 0.10)  # 부가세 10% (관세 포함 가액 기준)
        brokerage_fee = 30000  # 관세사 대행 수수료
    else:
        # [구매대행 모드] 미화 약 150달러(약 1000위안) 초과 시 세금 발생
        if price_cny > 1000:
            duty = int(price_krw * 0.08)
            vat = int((price_krw + duty) * 0.10)
        else:
            # 1000위안 이하 면세
            duty = 0
            vat = 0
            brokerage_fee = 0
            
    # 2. 최종 소싱 원가 도출
    total_customs = duty + vat + brokerage_fee
    total_sourcing_cost = price_krw + shipping_fee_krw + total_customs
    
    return {
        "price_krw": int(price_krw),
        "duty": duty,
        "vat": vat,
        "brokerage_fee": brokerage_fee,
        "total_customs": total_customs,
        "total_sourcing_cost": total_sourcing_cost
    }

if __name__ == "__main__":
    # 요청하신 테스트 케이스 실행
    test_prices = [50, 1200]
    
    print("\n💰 [소싱 원가 및 마진 시뮬레이션 테스트]\n" + "="*50)
    
    for cny in test_prices:
        print(f"\n[입력: 1688 상품 가격 {cny} CNY]")
        
        # 1. 개인 구매대행(B2C) 시뮬레이션
        b2c_res = calculate_customs_and_margin(cny, is_b2b=False)
        print(f" ▶ 개인 구매대행(B2C) 버전:")
        print(f"   - 물품 가액: {b2c_res['price_krw']:,}원")
        print(f"   - 통관 비용: {b2c_res['total_customs']:,}원 (관세:{b2c_res['duty']:,}/부가세:{b2c_res['vat']:,})")
        print(f"   - 최종 소싱 원가: {b2c_res['total_sourcing_cost']:,}원")
        
        # 2. 대량 사입(B2B) 시뮬레이션
        b2b_res = calculate_customs_and_margin(cny, is_b2b=True)
        print(f" ▶ 대량 사입(B2B) 버전:")
        print(f"   - 물품 가액: {b2b_res['price_krw']:,}원")
        print(f"   - 통관 비용: {b2b_res['total_customs']:,}원 (관세:{b2b_res['duty']:,}/부가세:{b2b_res['vat']:,}/수수료:{b2b_res['brokerage_fee']:,})")
        print(f"   - 최종 소싱 원가: {b2b_res['total_sourcing_cost']:,}원")
        
    print("\n" + "="*50)
