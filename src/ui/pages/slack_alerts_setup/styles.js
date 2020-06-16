import styled from 'styled-components';

export const BodyWrapper = styled.main`
    min-height: calc(100vh - 34px);
    padding: 0 25px;
    margin: 0;
    background: #f2f4f5;
    box-sizing: border-box;
`;

export const TitleWrapper = styled.section`
    padding-bottom: 15px;
    margin  -bottom: 15px;
    border-bottom: 1px solid #e1e6eb;
    box-sizing: border-box;
    overflow: hidden;
`;

export const DialogWrapper = styled.section`
    padding: 25px 0;
`;

export const Dialog = styled.div`
    margin: 0 auto;
    width: 740px;
    background: #fff;
    padding: 20px 40px;
    box-shadow: 0 1px 1px #e1e6eb;
`;

export const FormWrapper = styled.div`
    padding: 25px 25px 10px 25px;
`;

export const ButtonGroup = styled.div`
    border-top: 1px solid #e1e6eb;
    padding: 10px 0 0 0;
    display: flex;
    flex-direction: row;
    justify-content: flex-end;
    & > div {
        margin-left: 15px;
    }
`;